import math
from typing import Union


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

    @property
    def xy(self):
        return self.x, self.y


class Vec3:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.__x = float(x)
        self.__y = float(y)
        self.__z = float(z)

    def __str__(self):
        return "vec3{{ {:.6f}, {:.6f}, {:.6f} }}".format(self.x, self.y, self.z)

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, other: Union[float, "Vec3"]):
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        elif isinstance(other, float):
            return Vec3(self.x * other, self.y * other, self.z * other)
        else:
            raise ValueError("undefined multiplication: Vec3 with {}".format(type(other)))

    def __rmul__(self, other: Union[float, "Vec3"]):
        if isinstance(other, Vec3):
            return Vec3(self.x * other.x, self.y * other.y, self.z * other.z)
        elif isinstance(other, float):
            return Vec3(self.x * other, self.y * other, self.z * other)
        else:
            raise ValueError("undefined multiplication: Vec3 with {}".format(type(other)))

    def __eq__(self, other: "Vec3"):
        assert isinstance(other, Vec3)
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __getitem__(self, item: int):
        if 0 == item:
            return self.x
        elif 1 == item:
            return self.y
        elif 2 == item:
            return self.z
        else:
            raise IndexError()

    def __setitem__(self, key: int, value: float):
        if 0 == key:
            self.x = value
        elif 1 == key:
            self.y = value
        elif 2 == key:
            self.z = value
        else:
            raise IndexError()

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

    @property
    def xyz(self):
        return self.x, self.y, self.z

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

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

    def __str__(self):
        return "quat{{ w={:.6f}, x={:.6f}, y={:.6f}, z={:.6f} }}".format(self.w, self.x, self.y, self.z)

    def __eq__(self, other: "Quat"):
        assert isinstance(other, Quat)
        return (self.w, self.x, self.y, self.z) == (other.w, other.x, other.y, other.z)

    def isDefault(self) -> bool:
        return isFloatNear(self.w, 1) and isFloatNear(self.x, 0) and isFloatNear(self.y, 0) and isFloatNear(self.z, 0)

    def conjugate(self) -> "Quat":
        return Quat(self.w, -self.x, -self.y, -self.z)

    def productHamilton(self, other: "Quat") -> "Quat":
        a1 = self.w
        b1 = self.x
        c1 = self.y
        d1 = self.z

        a2 = other.w
        b2 = other.x
        c2 = other.y
        d2 = other.z

        return Quat(
            a1*a2 - b1*b2 - c1*c2 - d1*d2,
            a1*b2 + b1*a2 + c1*d2 - d1*c2,
            a1*c2 - b1*d2 + c1*a2 + d1*b2,
            a1*d2 + b1*c2 - c1*b2 + d1*a2
        )

    def rotateVec(self, v: Vec3) -> "Vec3":
        vq = Quat(0, v.x, v.y, v.z)
        q_star = self.conjugate()
        p_prime = self.productHamilton(vq).productHamilton(q_star)
        return Vec3(p_prime.x, p_prime.y, p_prime.z)

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

    def get(self, row: int, column: int) -> float:
        return self.__data[row][column]

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


class AABB3:
    def __init__(self):
        self.__min = Vec3()
        self.__max = Vec3()

    def __str__(self):
        return "AABB3{{ min=({}, {}, {}), max=({}, {}, {}) }}".format(
            self.__min.x, self.__min.y, self.__min.z,
            self.__max.x, self.__max.y, self.__max.z,
        )

    def resizeToContain(self, x: float, y: float, z: float):
        p = (float(x), float(y), float(z))

        for i in range(3):
            if p[i] < self.__min[i]:
                self.__min[i] = p[i]
            elif p[i] > self.__max[i]:
                self.__max[i] = p[i]

    @property
    def m_min(self):
        return self.__min

    @property
    def m_max(self):
        return self.__max
