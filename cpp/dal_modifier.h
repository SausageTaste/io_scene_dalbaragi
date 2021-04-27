#pragma once

#include "dal_struct.h"


namespace dal::parser {

    Mesh_Indexed convert_to_indexed(const Mesh_Straight& input);

    Mesh_IndexedJoint convert_to_indexed(const Mesh_StraightJoint& input);

    //Mesh_IndexedJoint convert_to_indexed(const Mesh_StraightJoint& input);

}
