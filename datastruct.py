from typing import List, Tuple, Generator, Callable, Any

import numpy as np

from . import byteutils as byt


class Mat4:
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

    def makeBinary(self) -> bytearray:
        floatlist = []
        for row in range(4):
            for col in range(4):
                floatlist.append(self.__data[row][col])

        return bytearray(np.array(floatlist, dtype=np.float32).tobytes())


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

    def makeJson(self):
        return {
            "roughness" : self.__roughness,
            "metallic" : self.__metallic,
            "diffuse map" : self.__diffuseMap,
            "roughness map" : self.__roughnessMap,
            "metallic map" : self.__metallicMap,
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


class Mesh:
    def __init__(self):
        self.__vertices = []
        self.__texcoords = []
        self.__normals =  []
        self.__boneWeights = []
        self.__boneIndices = []

    def makeBinary(self) -> bytearray:
        data = bytearray()

        v = np.array(self.__vertices, dtype=np.float32)
        t = np.array(self.__texcoords, dtype=np.float32)
        n = np.array(self.__normals, dtype=np.float32)

        assert 2*len(v) == 3*len(t) == 2*len(n)
        assert len(v) % 3 == 0
        numVertices = len(v) // 3

        hasBones = self.__hasBones()

        data += byt.to_int32(numVertices)
        data += byt.to_bool1(hasBones)

        data += v.tobytes()
        data += t.tobytes()
        data += n.tobytes()

        if hasBones:
            bw = np.array(self.__boneWeights, dtype=np.float32)
            bi = np.array(self.__boneIndices, dtype=np.int32)
            assert len(bw) == len(bi) == 3*numVertices

            data += bw.tobytes()
            data += bi.tobytes()

        return data

    def makeJson(self) -> dict:
        data = {
            "vertices"    : len(self.__vertices),
            "texcoords"   : len(self.__texcoords),
            "normals"     : len(self.__normals),
        }

        if self.__hasBones():
            data["boneWeights"] = len(self.__boneWeights)
            data["boneIndices"] = len(self.__boneIndices)

        return data

    def addVertex(self,
      xVert  : float, yVert  : float, zVert  : float,
      xTex   : float, yTex   : float,
      xNorm  : float, yNorm  : float, zNorm  : float,
      boneID0: int  , boneID1: int  , boneID2: int  ,
      weight0: float, weight1: float, weight2: float
    ) -> None:
        weightSum = weight0 + weight1 + weight2
        if 0 != weightSum:
            weight0 /= weightSum
            weight1 /= weightSum
            weight2 /= weightSum

        self.__vertices    += [ float( xVert ), float( yVert ), float( zVert ) ]
        self.__texcoords   += [ float( xTex  ), float( yTex  )                 ]
        self.__normals     += [ float( xNorm ), float (yNorm ), float( zNorm ) ]
        self.__boneWeights += [ float(weight0), float(weight1), float(weight2) ]
        self.__boneIndices += [   int(boneID0),   int(boneID1),   int(boneID2) ]

    def __hasBones(self) -> bool:
        for x in self.__boneWeights:
            if x != 0:
                return True
        else:
            return False


class RenderUnit:
    def __init__(self, name: str):
        self.__name = str(name)
        self.__mesh = Mesh()
        self.__material = Material()

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_nullTerminated(self.__name)
        data += self.__material.makeBinary()
        data += self.m_mesh.makeBinary()

        return data

    def makeJson(self) -> dict:
        return {
            "name" : self.__name,
            "mesh" : self.__mesh.makeJson(),
            "material" : self.__material.makeJson(),
        }

    @property
    def m_name(self):
        return self.__name

    @property
    def m_mesh(self):
        return self.__mesh

    @property
    def m_material(self):
        return self.__material
    @m_material.setter
    def m_material(self, m: Material):
        if not isinstance(m, Material):
            raise TypeError()
        else:
            self.__material = m


class Bone:
    def __init__(self, name: str):
        self.m_name = str(name)
        self.m_offsetMat = Mat4()
        self.m_parentIndex = -1

    def __str__(self):
        return "{{ name={}, parent={} }}".format(self.m_name, self.m_parentIndex)

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_nullTerminated(self.m_name)
        data += byt.to_int32(self.m_parentIndex)
        data += self.m_offsetMat.makeBinary()

        return data

    def makeJson(self) -> dict:
        return {
            "name" : self.m_name,
            "parent_index" : self.m_parentIndex,
        }


class SkeletonInterface:
    def __init__(self):
        self.__bones: List[Bone] = []

    def __str__(self):
        return "{{ {} }}".format(", ".join(str(x) for x in self.__bones))

    def __getitem__(self, i: int) -> Bone:
        return self.__bones[i]

    def __iter__(self):
        return iter(self.__bones)

    def __len__(self) -> int:
        return len(self.__bones)

    def makeBinary(self) -> bytearray:
        data = bytearray()

        data += byt.to_int32(len(self.__bones))
        for bone in self.__bones:
            data += bone.makeBinary()

        return data

    def makeJson(self) -> list:
        return [x.makeJson() for x in self.__bones]

    def getIndexOf(self, boneName: str) -> int:
        for i, bone in enumerate(self.__bones):
            if bone.m_name == boneName:
                return i
        else:
            raise RuntimeError("Bone name '{}' not found.".format(boneName))

    def makeIndexOf(self, boneName: str) -> int:
        try:
            _ = self.getIndexOf(boneName)
        except RuntimeError:
            self.__bones.append(Bone(boneName))
            return len(self.__bones) - 1
        else:
            raise RuntimeError("Bone already exists: {}".format(boneName))

    def getOrMakeIndexOf(self, boneName: str) -> int:
        try:
            found = self.getIndexOf(boneName)
        except RuntimeError:
            self.__bones.append(Bone(boneName))
            return len(self.__bones) - 1
        else:
            return found


class JointAnim:
    def __init__(self, name: str):
        self.__name = str(name)
        self.__transform = Mat4()

        # First float is time.
        self.__poses: List[Tuple[float, float, float, float]] = []
        self.__rotations: List[Tuple[float, float, float, float, float]] = []
        self.__scales: List[Tuple[float, float]] = []

    def makeBinary(self) ->bytearray:
        data = bytearray()

        data += self.__transform.makeBinary()

        poses = list(self.iterPoses())
        rotations = list(self.iterRotations())
        scales = list(self.iterScales())

        data += byt.to_int32(len(poses))
        for timepoint, value in poses:
            data += byt.to_float32(timepoint)
            data += byt.to_float32(value[0])
            data += byt.to_float32(value[1])
            data += byt.to_float32(value[2])

        data += byt.to_int32(len(rotations))
        for timepoint, value in rotations:
            data += byt.to_float32(timepoint)
            data += byt.to_float32(value[0])
            data += byt.to_float32(value[1])
            data += byt.to_float32(value[2])
            data += byt.to_float32(value[3])

        data += byt.to_int32(len(scales))
        for timepoint, value in scales:
            data += byt.to_float32(timepoint)
            data += byt.to_float32(value)

        return data

    def makeJson(self):
        return {
            "name" : self.__name,
            "poses" : ["{} : ( x={:0.6}, y={:0.6}, w={:0.6} )".format(timepoint, *value) for timepoint, value in self.iterPoses()],
            "rotations" : ["{} : ( x={:0.6}, y={:0.6}. z={:0.6}, w={:0.6} )".format(timepoint, *value) for timepoint, value in self.iterRotations()],
            "scales" : ["{} : {:0.6}".format(timepoint, value) for timepoint, value in self.iterScales()],
        }

    @property
    def m_name(self):
        return self.__name

    def iterPoses(self) -> Generator[Tuple[float, Tuple[float, float, float]], None, None]:
        self.__poses.sort()
        equalfunc = lambda xx, yy: (xx[1], xx[2], xx[3]) == (yy[1], yy[2], yy[3])
        newList = self.__removeDuplicate(self.__poses, equalfunc)

        for pos in newList:
            timepoint = pos[0]
            valvec = (pos[1], pos[2], pos[3])
            yield timepoint, valvec

    def iterRotations(self) -> Generator[Tuple[float, Tuple[float, float, float, float]], None, None]:
        self.__rotations.sort()
        equalfunc = lambda xx, yy: (xx[1], xx[2], xx[3], xx[4]) == (yy[1], yy[2], yy[3], yy[4])
        newList = self.__removeDuplicate(self.__rotations, equalfunc)

        for val in newList:
            timepoint = val[0]
            valvec = (val[1], val[2], val[3], val[4])
            yield timepoint, valvec

    def iterScales(self) -> Generator[Tuple[float, float], None, None]:
        self.__scales.sort()
        equalfunc = lambda xx, yy: xx[1] == yy[1]
        newList = self.__removeDuplicate(self.__scales, equalfunc)

        for pos in newList:
            timepoint = pos[0]
            scale = pos[1]
            yield timepoint, scale

    def addPos(self, timepoint: float, x: float, y: float, z: float):
        posTuple = ( float(timepoint), float(x), float(y), float(z) )
        self.__poses.append(posTuple)

    def addRotation(self, timepoint: float, x: float, y: float, z: float, w: float):
        rotTuple = ( float(timepoint), float(x), float(y), float(z), float(w) )
        self.__rotations.append(rotTuple)

    def addScale(self, timepoint: float, x: float):
        scaleTuple = ( float(timepoint), float(x) )
        self.__scales.append(scaleTuple)

    @staticmethod
    def __removeDuplicate(arr: List[Any], funcEqual: Callable[[Any, Any], bool]):
        arrSize = len(arr)
        newArr = [arr[0]]
        for i in range(1, arrSize):
            if not funcEqual(arr[i], newArr[-1]):
                newArr.append(arr[i])
        return newArr


class Animation:
    def __init__(self, name: str, skeleton: SkeletonInterface):
        self.__name = str(name)
        self.__durationTick = 0.0
        self.__tickPerSec = 0.0
        self.__joints: List[JointAnim] = [JointAnim(bone.m_name) for bone in skeleton]

    def makeBinary(self) -> bytearray:
        data = bytearray()

        assert 0.0 != self.__durationTick
        assert 0.0 != self.__tickPerSec

        data += byt.to_nullTerminated(self.__name)
        data += byt.to_float32(self.__durationTick)
        data += byt.to_float32(self.__tickPerSec)

        data += byt.to_int32(len(self.__joints))
        for joint in self.__joints:
            data += joint.makeBinary()

        return data

    def makeJson(self) -> dict:
        return {
            "name" : self.__name,
            "joints" : [x.makeJson() for x in self.__joints],
            "tick_per_sec" : self.__tickPerSec,
            "duration_tick" : self.__durationTick,
        }

    @property
    def m_joints(self):
        return self.__joints
    @property
    def m_name(self):
        return self.__name

    @property
    def m_durationTick(self):
        return self.__durationTick
    @m_durationTick.setter
    def m_durationTick(self, v: float):
        self.__durationTick = float(v)

    @property
    def m_tickPerSec(self):
        return self.__tickPerSec
    @m_tickPerSec.setter
    def m_tickPerSec(self, v: float):
        self.__tickPerSec = float(v)


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
