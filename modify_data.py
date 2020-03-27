from typing import List, Set, Dict, Iterable

from . import rawdata as rwd


class JointRemover:
    class _JointReplaceMap:
        def __init__(self, skeleton: rwd.Scene.Skeleton):
            self.__map = {"": ""}

            for joint in skeleton.m_joints:
                self.__map[joint.m_name] = joint.m_name

        def __len__(self) -> int:
            return len(self.__map)

        def __iter__(self):
            return self.__map.items()

        def __getitem__(self, name: str) -> str:
            return self.__map[name]

        def replace(self, from_name: str, to_name: str) -> None:
            for key in self.__map.keys():
                if self.__map[key] == from_name:
                    self.__map[key] = to_name

        def data(self):
            return self.__map

    @classmethod
    def process(cls, skel: rwd.Scene.Skeleton, anims: List[rwd.Scene.Animation], units: Iterable[rwd.Scene.RenderUnit]):
        # There is a better idea. Remove all useless joints in animations, and use that info to determine if remove
        # the joint from skeleton or not.

        uselesses = cls.__getSetOfNamesOfUselesses(anims[0])
        for anim in anims[1:]:
            uselesses = uselesses.intersection(cls.__getSetOfNamesOfUselesses(anim))
        uselesses = uselesses.difference(skel.getVitalJoints())

        replace_map = cls.__removeAndMakeReplaceMap(skel, uselesses)

        for anim in anims:
            anim.removeJoints(uselesses)

        for unit in units:
            if unit.m_mesh.m_skeletonName != skel.m_name:
                continue

            for vert in unit.m_mesh.vertices():
                for i, vert_joint in enumerate(vert.m_joints):
                    try:
                        vert.m_joints[i] = (vert_joint[0], replace_map[vert_joint[1]])
                    except KeyError:
                        pass

    @classmethod
    def __getSetOfNamesOfUselesses(cls, animation: rwd.Scene.Animation) -> Set[str]:
        assert isinstance(animation, rwd.Scene.Animation)

        result = set()
        for joint in animation.m_joints:
            if joint.isUseless():
                result.add(joint.m_name)
        return result

    @classmethod
    def __removeAndMakeReplaceMap(cls, skeleton: rwd.Scene.Skeleton, remove_list: Set[str]) -> Dict[str, str]:
        replace_map = cls._JointReplaceMap(skeleton)

        # make replace map
        skeleton.assertJointOrder()
        for i in reversed(range(len(skeleton.m_joints))):
            joint = skeleton.m_joints[i]
            parent_name = joint.m_parentName
            if joint.m_name in remove_list:
                replace_map.replace(joint.m_name, parent_name)

        # remove joints and replace parent names
        new_joints: List[rwd.Scene.Joint] = []
        for joint in skeleton.m_joints:
            if joint.m_name not in remove_list:
                joint.m_parentName = replace_map[joint.m_parentName]
                new_joints.append(joint)
        skeleton.m_joints = new_joints

        return replace_map.data()
