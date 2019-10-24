import base64

import zlib
import numpy as np


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

    def makeJson(self):
        return {
            "roughness" : self.__roughness,
            "metallic" : self.__metallic,
            "diffuse_map" : self.__diffuseMap,
            "roughness_map" : self.__roughnessMap,
            "metallic_map" : self.__metallicMap,
        }

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

    def getVertexArrays(self):
        v = np.array(self.__vertices, dtype=np.float32)
        t = np.array(self.__texcoords, dtype=np.float32)
        n = np.array(self.__normals, dtype=np.float32)
        return v, t, n

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

    def makeJson(self, compress: bool):
        if (compress):
            data: bytes = zlib.compress(self.__array, zlib.Z_BEST_COMPRESSION)
        else:
            data: bytes = self.__array
        return {
            "size" : len(self.__array),
            "zipped_array" : base64.encodebytes(data).decode("utf8")
        }


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
