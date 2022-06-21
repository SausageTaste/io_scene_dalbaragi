#include <vector>

#include <fmt/format.h>

#include "include_python.h"


// Type: BinaryBuilder
namespace {
namespace BinaryBuilder {

    class ClassDef {

    private:
        std::vector<uint8_t> data_;

    public:
        auto data() const {
            return this->data_.data();
        }

        auto size() const {
            return this->data_.size();
        }

        std::pair<size_t, size_t> add_bin_array(const uint8_t* const buf, const size_t size) {
            const auto start_index = this->data_.size();
            this->data_.insert(this->data_.end(), buf, buf + size);
            const auto end_index = this->data_.size();
            return std::make_pair(start_index, end_index - start_index);
        }

    };


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

        // Type
        if (PyType_Ready(&::BinaryBuilder::type) < 0)
            return nullptr;
        Py_INCREF(&::BinaryBuilder::type);
        if (PyModule_AddObject(modu, "BinaryBuilder", reinterpret_cast<PyObject*>(&::BinaryBuilder::type)) < 0) {
            Py_DECREF(&::BinaryBuilder::type);
            Py_DECREF(modu);
            return nullptr;
        }

        return modu;
    }

}
