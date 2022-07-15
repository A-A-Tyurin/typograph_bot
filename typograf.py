from enum import IntEnum, unique
from http import HTTPStatus
from xml.etree import ElementTree

import requests


@unique
class TypografEntityType(IntEnum):
    LETTER = 1
    NUMBER = 2
    SYMBOL = 3


class Typograf:
    __slots__ = 'entity_type', 'use_br', 'use_p', 'max_nobr'
    __REQUEST_BODY_TEMPLATE = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
                'xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '  <soap:Body>'
        '     <ProcessText xmlns="http://typograf.artlebedev.ru/webservices/">'
        '        <text>{text}</text>'
        '        <entityType>{entity_type}</entityType>'
        '        <useBr>{use_br}</useBr>'
        '        <useP>{use_p}</useP>'
        '        <maxNobr>{max_nobr}</maxNobr>'
        '     </ProcessText>'
        '   </soap:Body>'
        '</soap:Envelope>'
    )
    __REQUEST_URL = 'http://typograf.artlebedev.ru/webservices/typograf.asmx'
    __REQUEST_HEADERS = {
        'Content-Type': 'text/xml',
        'SOAPAction': 'http://typograf.artlebedev.ru/webservices/ProcessText'
    }

    def __init__(
        self,
        entity_type: TypografEntityType = TypografEntityType.SYMBOL,
        use_br: bool = False,
        use_p: bool = False,
        max_nobr: int = 0
    ) -> None:
        self.entity_type = entity_type
        self.use_br = use_br
        self.use_p = use_p
        self.max_nobr = max_nobr

    def process_text(self, text: str) -> str:
        text = (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;'))
        params = {
            'url': self.__REQUEST_URL,
            'headers': self.__REQUEST_HEADERS,
            'data': self.__REQUEST_BODY_TEMPLATE.format(
                text=text,
                entity_type=self.entity_type,
                use_br=int(self.use_br),
                use_p=int(self.use_p),
                max_nobr=self.max_nobr
            ).encode('utf-8')
        }

        try:
            response = requests.post(**params)
            if response.status_code != HTTPStatus.OK:
                raise ConnectionError(
                    'Wrong response code: '
                    f'params = {params}; '
                    f'code = {response.status_code}; '
                    f'reason = {response.reason}; '
                    f'content = {response.text}'
                )

            root = ElementTree.fromstring(response.content.decode('utf-8'))
            element = root.find(
                './soap:Body/typograf:ProcessTextResponse/typograf:ProcessTextResult',
                namespaces={
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'typograf': 'http://typograf.artlebedev.ru/webservices/'
                }
            )
            if element is None:
                raise KeyError(
                    'Unexpected response format. '
                    'ProcessTextResult element not found'
                )
            if element.text.lower() == 'error: unknown action or encoding':
                raise ValueError(
                    'Unexpected response format. '
                    'ProcessTextResult contains error text'
                )
            return (element.text.replace('&amp;', '&')
                                .replace('&lt;', '<')
                                .replace('&gt;', '>'))
        except requests.RequestException as error:
            raise ConnectionError(
                f'Unexcepted error during request: {error}; '
                f'params = {params}'
            ) from error
        except ElementTree.ParseError as error:
            raise TypeError(
                'Incorrect response type.'
                f'params = {params}'
                f'content = {response.text}'
            ) from error
