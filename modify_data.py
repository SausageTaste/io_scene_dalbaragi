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
    def process(cls, skel: rwd.Scene.Skeleton, anims: List[rwd.Scene.Animation], models: Iterable[rwd.Scene.Model]):
        # There is a better idea. Remove all useless joints in animations, and use that info to determine whether remove
        # a joint from the skeleton or not.

        uselesses = cls.__getSetOfNamesOfUselesses(anims[0])
        for anim in anims[1:]:
            uselesses = uselesses.intersection(cls.__getSetOfNamesOfUselesses(anim))
        uselesses = uselesses.difference(skel.getVitalJoints())

        replace_map = cls.__removeAndMakeReplaceMap(skel, uselesses)

        for anim in anims:
            anim.removeJoints(uselesses)

        for model in models:
            for unit in model.m_renderUnits:
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


'''
class MaterialDuplacateRemover:
    @classmethod
    def process(cls, units: Dict[int, rwd.Scene.RenderUnit], static_actors: List[rwd.Scene.StaticActor]) -> None:
        replace_map = cls.__makeReplaceMap(units)

        for id_removed, id_preserved in replace_map.items():
            for actor in static_actors:
                if id_preserved == actor.m_renderUnitID:
                    actor_of_preserved = actor
                    break
            else:
                raise RuntimeError()

            for actor in static_actors:
                if id_removed == actor.m_renderUnitID:
                    units[id_preserved].m_mesh.concatenate(units[id_removed].m_mesh)
                    actor_of_preserved.m_name += "+" + actor.m_name
                    del units[id_removed]
                    actor.m_renderUnitID = 0

        static_actors_tmp = static_actors[:]
        static_actors.clear()
        for actor in static_actors_tmp:
            if 0 != actor.m_renderUnitID:
                static_actors.append(actor)

    @classmethod
    def __makeReplaceMap(cls, units: Dict[int, rwd.Scene.RenderUnit]) -> Dict[int, int]:
        preserved: Set[int] = set()
        replace_map: Dict[int, int] = {}  # id to remove, id to preserve

        for uid in units.keys():
            for uid_preserved in preserved:
                if units[uid].m_material.isSame(units[uid_preserved].m_material):
                    replace_map[uid] = uid_preserved
                    break
            else:
                preserved.add(uid)

        return replace_map
'''
