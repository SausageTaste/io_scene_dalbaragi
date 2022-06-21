#include <vector>
#include <optional>
#include <stdexcept>
#include <unordered_map>

#include <fmt/format.h>

#include "include_python.h"
#include "mesh_manager.h"


// Type: BinaryBuilder
namespace {
namespace BinaryBuilder {

    using ClassDef = b3dsung::BinaryBuilder;


    struct ObjectDef {
        PyObject_HEAD;
        ClassDef impl_;
    };


    std::vector<PyMemberDef> members{
        {nullptr}
    };


    // Magic methods

    void magic_dealloc(ObjectDef* const self) {
        self->impl_.~ClassDef();
        Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
    }

    PyObject* magic_new(PyTypeObject* const type, PyObject* const args, PyObject* const kwds) {
        const auto self = reinterpret_cast<ObjectDef*>(type->tp_alloc(type, 0));
        if (nullptr == self)
            return nullptr;

        new (&self->impl_) ClassDef{};
        return reinterpret_cast<PyObject*>(self);
    }

    int magic_init(ObjectDef* const self, PyObject* const args, PyObject* const kwds) {
        return 0;
    }

    std::vector<PyGetSetDef> getsetters{
        {nullptr}
    };


    // Methods

    PyObject* get_data(ObjectDef* const self, PyObject* const _) {
        const auto buf = reinterpret_cast<const char*>(self->impl_.data());
        const auto size = self->impl_.size();
        return PyBytes_FromStringAndSize(buf, size);
    }

    PyObject* add_bin_array(ObjectDef* const self, PyObject* const args) {
        Py_buffer buffer;
        if (!PyArg_ParseTuple(args, "y*", &buffer)) {
            return nullptr;
        }

        auto [index, size] = self->impl_.add_bin_array(reinterpret_cast<const uint8_t*>(buffer.buf), buffer.len);
        return Py_BuildValue("(II)", index, size);
    }

    std::vector<PyMethodDef> methods{
        {"get_data", reinterpret_cast<PyCFunction>(get_data), METH_NOARGS, ""},
        {"add_bin_array", reinterpret_cast<PyCFunction>(add_bin_array), METH_VARARGS, ""},
        {nullptr}
    };

    // Definition

    auto type = []() {
        PyTypeObject output = {PyObject_HEAD_INIT(nullptr) 0};
        output.tp_name = "b3dsung.BinaryBuilder";
        output.tp_doc = "BinaryBuilder objects";
        output.tp_basicsize = sizeof(ObjectDef);
        output.tp_itemsize = 0;
        output.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
        output.tp_new = magic_new;
        output.tp_init = reinterpret_cast<initproc>(magic_init);
        output.tp_dealloc = reinterpret_cast<destructor>(magic_dealloc);
        output.tp_members = members.data();
        output.tp_methods = methods.data();
        output.tp_getset = getsetters.data();
        return output;
    }();

}
}


namespace {

    class JointIndexMap {

    private:
        std::unordered_map<std::string, int32_t> data_;

    public:
        void set(std::string k, int32_t v) {
            this->data_[k] = v;
        }

        std::optional<int32_t> get(const std::string& k) const {
            const auto found = this->data_.find(k);
            if (this->data_.end() != found) {
                return found->second;
            }
            else {
                return std::nullopt;
            }
        }

        auto size() const {
            return this->data_.size();
        }

    };


    PyObject* get_py_attr(PyObject* obj, const char* const attr_name) {
        const auto output = PyObject_GetAttrString(obj, attr_name);
        if (nullptr == output)
            throw std::runtime_error{""};
        else
            return output;
    }

    bool parse_mesh(b3dsung::Mesh& output, PyObject* const bpy_mesh, PyObject* const skeleton_name, const JointIndexMap& joint_index_map) {
        const auto mesh_data_obj = ::get_py_attr(bpy_mesh, "data");
        const auto mesh_name_obj = ::get_py_attr(mesh_data_obj, "name");

        PyObject_CallMethodNoArgs(mesh_data_obj, PyUnicode_FromString("calc_loop_triangles"));

        output.name_ = PyUnicode_AsUTF8(mesh_name_obj);
        if (!PyUnicode_Check(skeleton_name))
            throw std::runtime_error{""};
        output.skeleton_name_ = PyUnicode_AsUTF8(skeleton_name);

        const auto loop_tri_iter = PyObject_GetIter(::get_py_attr(mesh_data_obj, "loop_triangles"));
        if (nullptr == loop_tri_iter)
            throw std::runtime_error{""};

        while (const auto tri = PyIter_Next(loop_tri_iter)) {

            Py_DECREF(tri);
        }

        Py_DECREF(loop_tri_iter);


        return true;
    }

}


// Type: MeshManager
namespace {
namespace MeshManager {

    using ClassDef = b3dsung::MeshManager;


    struct ObjectDef {
        PyObject_HEAD;
        ClassDef impl_;
    };


    std::vector<PyMemberDef> members{
        {nullptr}
    };


    // Magic methods

    void magic_dealloc(ObjectDef* const self) {
        self->impl_.~ClassDef();
        Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
    }

    PyObject* magic_new(PyTypeObject* const type, PyObject* const args, PyObject* const kwds) {
        const auto self = reinterpret_cast<ObjectDef*>(type->tp_alloc(type, 0));
        if (nullptr == self)
            return nullptr;

        new (&self->impl_) ClassDef{};
        return reinterpret_cast<PyObject*>(self);
    }

    int magic_init(ObjectDef* const self, PyObject* const args, PyObject* const kwds) {
        return 0;
    }

    std::vector<PyGetSetDef> getsetters{
        {nullptr}
    };


    // Methods

    PyObject* get_mesh_mat_pairs(ObjectDef* const self, PyObject* const arg) {
        return Py_None;
    }

    PyObject* add_bpy_mesh(ObjectDef* const self, PyObject* const args) try {
        PyObject* bpy_mesh = nullptr;
        PyObject* skeleton_name = nullptr;
        PyObject* joint_name_index_map = nullptr;
        if (!PyArg_ParseTuple(args, "OOO", &bpy_mesh, &skeleton_name, &joint_name_index_map))
            return nullptr;

        const auto mesh_data_obj = ::get_py_attr(bpy_mesh, "data");
        const auto mesh_name_obj = ::get_py_attr(mesh_data_obj, "name");
        std::string mesh_name = PyUnicode_AsUTF8(mesh_name_obj);

        // Joint index map
        ::JointIndexMap joint_index_map;
        {
            if (!PyDict_Check(joint_name_index_map))
                return nullptr;

            const auto keys = PyDict_Keys(joint_name_index_map);
            const auto key_count = PyList_Size(keys);

            for (Py_ssize_t i = 0; i < key_count; ++i) {
                const auto key = PyList_GetItem(keys, i);
                if (!PyUnicode_Check(key))
                    return nullptr;

                const auto value = PyDict_GetItem(joint_name_index_map, key);
                if (!PyLong_Check(value))
                    return nullptr;

                joint_index_map.set(
                    PyUnicode_AsUTF8(key),
                    PyLong_AsLong(value)
                );
            }
        }

        if (!self->impl_.has_mesh(mesh_name.c_str())) {
            const auto result = ::parse_mesh(self->impl_.new_mesh(mesh_name.c_str()), bpy_mesh, skeleton_name, joint_index_map);
            if (!result)
                return nullptr;
        }

        return mesh_name_obj;
    }
    catch (const std::runtime_error&) {
        return nullptr;
    }

    PyObject* make_json(ObjectDef* const self, PyObject* const arg) {
        return Py_None;
    }

    std::vector<PyMethodDef> methods{
        {"get_mesh_mat_pairs", reinterpret_cast<PyCFunction>(get_mesh_mat_pairs), METH_O, ""},
        {"add_bpy_mesh", reinterpret_cast<PyCFunction>(add_bpy_mesh), METH_VARARGS, ""},
        {"make_json", reinterpret_cast<PyCFunction>(make_json), METH_O, ""},
        {nullptr}
    };

    // Definition

    auto type = []() {
        PyTypeObject output = {PyObject_HEAD_INIT(nullptr) 0};
        output.tp_name = "b3dsung.MeshManager";
        output.tp_doc = "MeshManager objects";
        output.tp_basicsize = sizeof(ObjectDef);
        output.tp_itemsize = 0;
        output.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
        output.tp_new = magic_new;
        output.tp_init = reinterpret_cast<initproc>(magic_init);
        output.tp_dealloc = reinterpret_cast<destructor>(magic_dealloc);
        output.tp_members = members.data();
        output.tp_methods = methods.data();
        output.tp_getset = getsetters.data();
        return output;
    }();

}
}


// Module definitions
namespace {

    std::vector<PyMethodDef> module_functions{
        {nullptr, nullptr, 0, nullptr}
    };

    PyModuleDef module_def = {
        PyModuleDef_HEAD_INIT,
        "b3dsung",
        "Python interface for the b3dsung C library function",
        -1,
        ::module_functions.data()
    };

    PyMODINIT_FUNC PyInit_b3dsung() {
        PyObject* const modu = PyModule_Create(&module_def);
        if (nullptr == modu)
            return nullptr;

        // Type: BinaryBuilder
        if (PyType_Ready(&::BinaryBuilder::type) < 0)
            return nullptr;
        Py_INCREF(&::BinaryBuilder::type);
        if (PyModule_AddObject(modu, "BinaryBuilder", reinterpret_cast<PyObject*>(&::BinaryBuilder::type)) < 0) {
            Py_DECREF(&::BinaryBuilder::type);
            Py_DECREF(modu);
            return nullptr;
        }

        // Type: MeshManager
        if (PyType_Ready(&::MeshManager::type) < 0)
            return nullptr;
        Py_INCREF(&::MeshManager::type);
        if (PyModule_AddObject(modu, "MeshManager", reinterpret_cast<PyObject*>(&::MeshManager::type)) < 0) {
            Py_DECREF(&::MeshManager::type);
            Py_DECREF(modu);
            return nullptr;
        }

        return modu;
    }

}
