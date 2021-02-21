
def loop_wrapper(debugger):
    def _except_wrapper(func):
        def _wrap_func(self, *args):
            debugger.debug('[{}]해당 함수를 실행합니다.'.format(func.__name__))
            for _ in range(3):
                try:
                    func(self, *args)
                    break
                except:
                    debugger.exception('데이터 수집 실패, 페이지 새로고침 이후 재시도합니다.')
            else:
                debugger.debug('[{}]해당 함수는 값이 정상적으로 수집되지 않아 실패처리 되었습니다.'.format(func.__name__))
        return _wrap_func
