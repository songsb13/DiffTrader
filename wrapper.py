import functools
import logging
import time


def loop_wrapper(debugger):
    """
        wrapper that try loop up to 3 times
        It is used when defining variable information, fee, deposits, compare_orderbook and etc.
    """
    def _except_wrapper(func):
        def _wrap_func(self, *args):
            for _ in range(3):
                data = func(self, *args)
                if data is not None:
                    return data
                else:
                    debugger.debug(
                        'function [{}] is failed to setting a function.'.format(func.__name__))
                    time.sleep(5)
            else:
                debugger.debug('function [{}] is failed to setting a function, please try later.'.format(func.__name__))
                raise
        return _wrap_func
    return _except_wrapper



@loop_wrapper(debugger=logging)
def test(self, data):
    print('hi!')
    return 'testcode'


ret = test('', 'datacode')

print(ret)