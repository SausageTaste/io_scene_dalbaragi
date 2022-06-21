#include <vector>

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

    PyObject* add_bpy_mesh(ObjectDef* const self, PyObject* const args) {
        return Py_None;
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
