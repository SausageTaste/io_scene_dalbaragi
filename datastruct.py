import base64

import numpy as np

from . import byteutils as byt


class Material:
    def __init__(self):
        self.__roughness = 0.5
        self.__metallic = 0.0

        self.__diffuseMap = ""
        self.__roughnessMap = ""
        self.__metallicMap = ""

    def __eq__(self, other) -> bool:
        if   self.__roughness != other.__roughness:
            return False
        elif self.__metallic != other.__metallic:
            return False
        elif self.__diffuseMap != other.__diffuseMap:
            return False
        elif self.__roughnessMap != other.__roughnessMap:
            return False
        elif self.__metallicMap != other.__metallicMap:
            return False
        else:
            return True

    def __str__(self):
        return "Material{{ roughness={}, metallic={}, diffuse map={}, roughness map={}, metallic map={} }}".format(
            self.__roughness, self.__metallic, self.__diffuseMap, self.__roughnessMap, self.__metallicMap
        )

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_float32(self.__roughness)
        data += byt.to_float32(self.__metallic)
        data += byt.to_nullTerminated(self.__diffuseMap)
        data += byt.to_nullTerminated(self.__roughnessMap)
        data += byt.to_nullTerminated(self.__metallicMap)

        return data

    @property
    def m_roughness(self):
        return self.__roughness
    @m_roughness.setter
    def m_roughness(self, v: float):
        self.__roughness = float(v)

    @property
    def m_metallic(self):
        return self.__metallic
    @m_metallic.setter
    def m_metallic(self, v: float):
        self.__metallic = float(v)

    @property
    def m_diffuseMap(self):
        return self.__diffuseMap
    @m_diffuseMap.setter
    def m_diffuseMap(self, v: str):
        self.__diffuseMap = str(v)

    @property
    def m_roughnessMap(self):
        return self.__roughnessMap
    @m_roughnessMap.setter
    def m_roughnessMap(self, v: str):
        self.__roughnessMap = str(v)

    @property
    def m_metallicMap(self):
        return self.__metallicMap
    @m_metallicMap.setter
    def m_metallicMap(self, v: str):
        self.__metallicMap = str(v)


class RenderUnit:
    def __init__(self, name: str):
        self.__name = str(name)

        self.__vertices = []
        self.__texcoords = []
        self.__normals = []

        self.__material = Material()

    def addVertex(self, xVert, yVert, zVert, xTex, yTex, xNorm, yNorm, zNorm):
        self.__vertices +=  [ float(xVert), float(yVert), float(zVert) ]
        self.__texcoords += [ float(xTex ), float(yTex )               ]
        self.__normals +=   [ float(xNorm), float(yNorm), float(zNorm) ]

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_nullTerminated(self.__name)
        data += self.__material.makeBinary()

        v = np.array(self.__vertices, dtype=np.float32)
        t = np.array(self.__texcoords, dtype=np.float32)
        n = np.array(self.__normals, dtype=np.float32)

        assert 2*len(v) == 3*len(t) == 2*len(n)
        assert len(v) % 3 == 0
        numVertices = len(v) // 3

        data += byt.to_int32(numVertices)
        data += v.tobytes()
        data += t.tobytes()
        data += n.tobytes()

        return data

    def makeReadable(self) -> str:
        return f"""RenderUnit{{
    float roughness = {self.__material.m_roughness}
    float metallic = {self.__material.m_metallic}
    str diffuse map = "{self.__material.m_diffuseMap}"
    str roughness map = "{self.__material.m_roughnessMap}"
    str metallic map = "{self.__material.m_metallicMap}"

    float vertices[{len(self.__vertices)}] = {{
        {", ".join(str(x) for x in self.__vertices)}
    }}
    float texcoords[{len(self.__texcoords)}] = {{
        {", ".join(str(x) for x in self.__texcoords)}
    }}
    float normals[{len(self.__normals)}] = {{
        {", ".join(str(x) for x in self.__normals)}
    }}
}}
        """

    def iterVertices(self):
        return iter(self.__vertices)
    def iterTexcoords(self):
        return iter(self.__texcoords)
    def iterNormals(self):
        return iter(self.__normals)

    @property
    def m_name(self):
        return self.__name

    @property
    def m_material(self):
        return self.__material
    @m_material.setter
    def m_material(self, m: Material):
        if not isinstance(m, Material):
            raise TypeError()
        else:
            self.__material = m


class Datablock:
    def __init__(self):
        self.__array = bytearray()
    
    def addData(self, arr: bytearray) -> int:
        offset = len(self.__array)
        self.__array += arr
        return offset

    def getSize(self) -> int:
        return len(self.__array)

    @property
    def m_array(self) -> bytearray:
        return self.__array


class IndexSet:
    def __init__(self, valType):
        self.__valType = valType
        self.__list = []

    def __iter__(self):
        return iter(self.__list)

    def addGetIndex(self, val):
        if not isinstance(val, self.__valType):
            raise TypeError("Expected type '{}', got '{}' instead.".format(self.__valType, type(val)))
        else:
            found = self.__findIndex(val)
            if -1 != found:
                return found
            else:
                index = len(self.__list)
                self.__list.append(val)
                return index

    def __findIndex(self, val) -> int:
        for i, e in enumerate(self.__list):
            if e == val:
                return i
        else:
            return -1
