import math


EPSILON = 1.0 / 1000.0


def isFloatNear(v: float, criteria: float):
    assert isinstance(v, float)
    criteria = float(criteria)

    return (criteria - EPSILON) < v < (criteria + EPSILON)


class Vec2:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.__x = float(x)
        self.__y = float(y)

    @property
    def x(self):
        return self.__x
    @x.setter
    def x(self, value: float):
        self.__x = float(value)
    @property
    def y(self):
        return self.__y
    @y.setter
    def y(self, value: float):
        self.__y = float(value)


class Vec3:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.__x = float(x)
        self.__y = float(y)
        self.__z = float(z)

    def __eq__(self, other: "Vec3"):
        assert isinstance(other, Vec3)
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def isDefault(self) -> bool:
        return isFloatNear(self.x, 0) and isFloatNear(self.y, 0) and isFloatNear(self.z, 0)

    @property
    def x(self):
        return self.__x
    @x.setter
    def x(self, value: float):
        self.__x = float(value)
    @property
    def y(self):
        return self.__y
    @y.setter
    def y(self, value: float):
        self.__y = float(value)
    @property
    def z(self):
        return self.__z
    @z.setter
    def z(self, value: float):
        self.__z = float(value)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def lengthSqr(self) -> float:
        return self.dot(self)

    def length(self) -> float:
        return math.sqrt(self.lengthSqr())

    def normalize(self) -> None:
        length = self.length()
        self.x /= length
        self.y /= length
        self.z /= length


class Quat:
    def __init__(self, w: float = 1.0, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.__w = float(w)
        self.__x = float(x)
        self.__y = float(y)
        self.__z = float(z)

    def __eq__(self, other: "Quat"):
        assert isinstance(other, Quat)
        return (self.w, self.x, self.y, self.z) == (other.w, other.x, other.y, other.z)

    def isDefault(self) -> bool:
        return isFloatNear(self.w, 1) and isFloatNear(self.x, 0) and isFloatNear(self.y, 0) and isFloatNear(self.z, 0)

    @property
    def w(self):
        return self.__w
    @w.setter
    def w(self, value: float):
        self.__w = float(value)
    @property
    def x(self):
        return self.__x
    @x.setter
    def x(self, value: float):
        self.__x = float(value)
    @property
    def y(self):
        return self.__y
    @y.setter
    def y(self, value: float):
        self.__y = float(value)
    @property
    def z(self):
        return self.__z
    @z.setter
    def z(self, value: float):
        self.__z = float(value)


class Mat4:
    # Representation is row major.
    def __init__(self):
        self.__data = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ]

    def set(self, mat):
        for row in range(4):
            for col in range(4):
                self.__data[row][col] = mat[row][col]

    def makeReadable(self) -> str:
        col_strings = []

        for col in range(4):
            col_values = []
            for row in range(4):
                numstr = "{:0.2}".format(self.__data[row][col])
                col_values.append(numstr)
            colstr = ", ".join(col_values)
            col_strings.append("( {} )".format(colstr))

        return ", ".join(col_strings)


class AABB:
    def __init__(self):
        self.__min = [0.0, 0.0, 0.0]
        self.__max = [0.0, 0.0, 0.0]

    def __str__(self):
        return "AABB{{ min=({}, {}, {}), max=({}, {}, {}) }}".format(*self.__min, *self.__max)

    def resizeToContain(self, x, y, z):
        p = [x, y, z]

        for i in range(3):
            if p[i] < self.__min[i]:
                self.__min[i] = p[i]
            elif p[i] > self.__max[i]:
                self.__max[i] = p[i]
