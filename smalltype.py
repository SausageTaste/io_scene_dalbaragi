import math


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
