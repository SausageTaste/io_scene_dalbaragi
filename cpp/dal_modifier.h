#pragma once

#include "dal_struct.h"


namespace dal::parser {

    Mesh_Indexed convert_to_indexed(const Mesh_Straight& input);

    Model_Straight merge_by_material(const Model_Straight& model);

}
