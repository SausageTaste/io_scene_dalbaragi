
class FixedNumer1000:
    __FIXED_DENOM = 1000

    def __init__(self, v: float = 0.0):
        self.__data = 0
        self.set(v)

    def __str__(self):
        a = ['0', '0', '0', '0'] + list(str(self.__data))
        b = "".join(a[:-3]) + '.' + "".join(a[-3:])
        b = b.strip('0')
        if b.startswith('.'):
            b = '0' + b
        if b.endswith('.'):
            b = b[:-1]
        return b

    def __add__(self, other: "FixedNumer1000"):
        new_one = FixedNumer1000()
        new_one.__data = round(self.__data + other.__data)
        return new_one

    def __sub__(self, other: "FixedNumer1000"):
        new_one = FixedNumer1000()
        new_one.__data = round(self.__data - other.__data)
        return new_one

    def __mul__(self, other: "FixedNumer1000"):
        new_one = FixedNumer1000()
        new_one.__data = round(self.__data * other.__data / self.__FIXED_DENOM)
        return new_one

    def __truediv__(self, other: "FixedNumer1000"):
        new_one = FixedNumer1000()
        new_one.__data = round(self.__data / other.__data * self.__FIXED_DENOM)
        return new_one

    def __float__(self):
        return float(self.__data) / float(self.__FIXED_DENOM)

    def set(self, v: float) -> None:
        self.__data = round(v * self.__FIXED_DENOM)


fixed_t = FixedNumer1000


def main():
    import random

    a_float = random.randint(1, 999) / 10
    b_float = random.randint(1, 999) / 10

    a_fixed = fixed_t(a_float)
    b_fixed = fixed_t(b_float)

    print("Float: {} / {} = {}".format(a_float, b_float, a_float / b_float))
    print("Fixed: {} / {} = {}".format(a_fixed, b_fixed, a_fixed / b_fixed))

if __name__ == '__main__':
    main()
