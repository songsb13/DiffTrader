"""
    각 프로세스마다 별도의 로깅 파일을 가진다.
    기록되는 datetime은 UTC를 기본으로 한다.
    경로: /logs/{process_name}/{Y-m-d}/{H:M:S}

    1. 로테이팅 정책
        1. 날짜별 폴더
        2. maxBytes=10 * 1024 * 1024
        3. 파일명은 로깅 시작 datetime
    2. 로깅 정책
        1. Debug
            - 클래스단위, 함수단위에 들어가고 나갈때 작성한다.
            - prefix는 [datetime][level][process_name][function][parameters][message]순
                ex) [2022-05-15T15:30:30][monitoring][get_deposit_addrs][ad='adff'][fail..]
            - 메세지는 영어로 작성한다.
        2. Info
            - 유저에게 notice하기 위한 로깅.
            - 별도 prefix없이 메세지만 기록한다.
            - 한국어로 작성한다.
        3. Warning
            - prefix는 debug와 동일하다.
            - 함수단위에서 실패해서 재시도할때 등 프로그램이 지속가능한 에러 수준일 때 기록한다.
        4. Error
            - prefix는 debug와 동일하다.
            - 함수단위에서 재시도가 더이상 안되는 등 프로그램이 지속불가능한 에러 수준일 때 기록한다.
        5. Critical
            - prefix는 debug와 동일하다.
            - 외부 요인이 아닌 Memory leak, 코드에서 발생하는 에러 수준일 때 기록한다.
"""
import datetime
import logging
import logging.config
import os.path


class LoggingFileHandler(logging.FileHandler):
    def __init__(self, process_name, filename, mode):
        super(LoggingFileHandler, self).__init__(filename, mode)
        self._filename = filename

    def filter(self, record) -> bool:
        if self._filename is None:
            pass



LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "simple": {
            "format": "[%(name)s][%(message)s]"
        },
        "complex": {
            "format": "[%(asctime)s][%(levelname)s][%(filename)s][%(funcName)s][%(message)s]"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
        },
        "file": {
            "class": "LoggingFileHandler",
            "process_name": '',
            "filename": "{}.log",
            "formatter": "complex",
            "level": "DEBUG"
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG"
    },
    "loggers": {
        "parent": {"level": "INFO"},
        "parent.child": {"level": "DEBUG"}
    }
}

logging.config.dictConfig(config=LOGGING_CONFIG)

try:
    now = datetime.datetime.now()
    now_date = str(now.date())
    if not os.path.isdir('./logs'):
        os.mkdir('./logs')
    if not os.path.isdir(f'./logs/{now_date}'):
        os.mkdir(f'./logs/{now_date}')
    LOG_CONFIG['handlers']['fileHandler']['filename'] = logfullpath
except:
    pass