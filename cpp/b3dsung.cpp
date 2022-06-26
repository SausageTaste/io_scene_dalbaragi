#include <list>
#include <vector>
#include <future>
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

    class PythonObject {

    private:
        PyObject* obj_ = nullptr;
        bool need_dec_ref_ = false;

    public:
        PythonObject() = default;

        PythonObject(PyObject* const ptr, const bool need_dec_ref = false)
            : obj_(ptr)
            , need_dec_ref_(need_dec_ref)
        {

        }

        PythonObject(const char* const str)
            : obj_(PyUnicode_FromString(str))
            , need_dec_ref_(true)
        {

        }

        PythonObject(const long x)
            : obj_(PyLong_FromLong(x))
            , need_dec_ref_(true)
        {

        }

        PythonObject(const unsigned long x)
            : obj_(PyLong_FromUnsignedLong(x))
            , need_dec_ref_(true)
        {

        }

        PythonObject(const long long x)
            : obj_(PyLong_FromLongLong(x))
            , need_dec_ref_(true)
        {

        }

        PythonObject(const unsigned long long x)
            : obj_(PyLong_FromUnsignedLongLong(x))
            , need_dec_ref_(true)
        {

        }

        ~PythonObject() {
            if (this->need_dec_ref_ && nullptr != this->obj_) {
                //fmt::print("Decreasing ref from {}\n", obj_->ob_refcnt);
                Py_DECREF(this->obj_);
            }
            this->obj_ = nullptr;
        }

        // Copy

        PythonObject(const PythonObject&) = delete;

        PythonObject& operator=(const PythonObject&) = delete;

        // Move

        PythonObject(PythonObject&& rhs) {
            std::swap(this->obj_, rhs.obj_);
            std::swap(this->need_dec_ref_, rhs.need_dec_ref_);
        }

        PythonObject& operator=(PythonObject&& rhs) {
            std::swap(this->obj_, rhs.obj_);
            std::swap(this->need_dec_ref_, rhs.need_dec_ref_);
            return *this;
        }

        // Auxiliary

        PyObject* operator*() {
            return this->get();
        }

        const PyObject* operator*() const {
            return this->get();
        }

        PyObject* get() {
            this->assert_ready();
            return this->obj_;
        }

        const PyObject* get() const {
            this->assert_ready();
            return this->obj_;
        }

        PyObject** out_ptr() {
            return &this->obj_;
        }

        bool is_ready() const {
            return nullptr != this->obj_;
        }

        void assert_ready() const {
            if (!this->is_ready()) {
                throw std::runtime_error{ "PythonObject is pointing at nullptr" };
            }
        }

        void assert_no_py_error() const {
            if (nullptr != PyErr_Occurred()) {
                throw std::runtime_error{ "A Python exception occurred" };
            }
        }

        void set_dec_ref_in_dtor(const bool v) {
            this->need_dec_ref_ = v;
        }

        // For simple types

        bool is_none() const {
            if (!this->is_ready())
                return false;

            return Py_IsNone(obj_);
        }

        // For int

        bool is_int() const {
            if (!this->is_ready())
                return false;

            return PyLong_Check(obj_);
        }

        long as_long() const {
            this->assert_ready();
            const auto output = PyLong_AsLong(obj_);
            this->assert_no_py_error();
            return output;
        }

        long long as_llong() const {
            this->assert_ready();
            const auto output = PyLong_AsLongLong(obj_);
            this->assert_no_py_error();
            return output;
        }

        // For float

        double as_double() const {
            this->assert_ready();
            const auto output = PyFloat_AsDouble(obj_);
            this->assert_no_py_error();
            return output;
        }

        // For str

        bool is_str() const {
            if (!this->is_ready())
                return false;

            return PyUnicode_Check(obj_);
        }

        std::string as_str() const {
            this->assert_ready();
            const auto result = PyUnicode_AsUTF8(obj_);
            if (nullptr != result) {
                return result;
            }
            else {
                throw std::runtime_error{ "Failed PyUnicode_AsUTF8" };
            }
        }

        // For iter

        PythonObject iter_next() {
            return PythonObject{PyIter_Next(this->get()), true};
        }

        // For object

        bool is_true() const {
            this->assert_ready();
            return PyObject_IsTrue(obj_);
        }

        PythonObject get_iter() const {
            this->assert_ready();
            return PythonObject{PyObject_GetIter(obj_), true};
        }

        PythonObject get_attr(const char* const attr_name) {
            this->assert_ready();
            return PythonObject{PyObject_GetAttrString(this->obj_, attr_name)};
        }

        PythonObject get_item(PythonObject& key) {
            this->assert_ready();
            return PyObject_GetItem(obj_, *key);
        }

        PythonObject get_item(const char* const key) {
            this->assert_ready();
            return this->get_item(PythonObject(key));
        }

        PythonObject get_item(const int key) {
            static_assert(sizeof(int) <= sizeof(long));
            this->assert_ready();
            return this->get_item(PythonObject(static_cast<long>(key)));
        }

        PythonObject get_item(const long key) {
            this->assert_ready();
            return this->get_item(PythonObject(key));
        }

        PythonObject call_method_noargs(const char* const method_name) {
            this->assert_ready();
            return PyObject_CallMethodNoArgs(this->obj_, *PythonObject(method_name));
        }

    };


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


    void parse_mesh(b3dsung::Mesh& output, PythonObject& bpy_mesh, const std::string& skeleton_name, const JointIndexMap& joint_index_map) {
        auto obj_mesh = bpy_mesh.get_attr("data");

        obj_mesh.call_method_noargs("calc_loop_triangles");
        output.name_ = obj_mesh.get_attr("name").as_str();
        output.skeleton_name_ = skeleton_name;

        auto loop_tri_iter = obj_mesh.get_attr("loop_triangles").get_iter();
        while (true) {
            auto tri = loop_tri_iter.iter_next();
            if (!tri.is_ready())
                break;

            std::string material_name;
            try {
                auto material_index = tri.get_attr("material_index");
                material_name = obj_mesh.get_attr("materials").get_item(material_index).get_attr("name").as_str();
            }
            catch (const std::runtime_error&) {
                material_name = "";
            }

            for (long i = 0; i < 3; ++i) {
                auto& dst_vertex = output.new_vertex(material_name.c_str());

                // Vertex
                auto vertex_index = tri.get_attr("vertices").get_item(::PythonObject{i});
                auto vertex_data = obj_mesh.get_attr("vertices").get_item(vertex_index).get_attr("co");
                dst_vertex.pos_ = glm::vec3{
                    vertex_data.get_item(0).as_double(),
                    vertex_data.get_item(1).as_double(),
                    vertex_data.get_item(2).as_double()
                };

                // UV coord
                auto active_layers = obj_mesh.get_attr("uv_layers").get_attr("active");
                if (!active_layers.is_none()) {
                    auto uv_data = active_layers.get_attr("data").get_item(tri.get_attr("loops").get_item(i)).get_attr("uv");
                    dst_vertex.uv_coord_[0] = uv_data.get_item(0).as_double();
                    dst_vertex.uv_coord_[1] = uv_data.get_item(1).as_double();
                }
                else {
                    dst_vertex.uv_coord_[0] = 0;
                    dst_vertex.uv_coord_[1] = 0;
                }

                // Normal
                auto normal_data = tri.get_attr("use_smooth").is_true() ?
                    obj_mesh.get_attr("vertices").get_item(vertex_index).get_attr("normal") :
                    tri.get_attr("normal");

                dst_vertex.normal_ = glm::vec3{
                    normal_data.get_item(0).as_double(),
                    normal_data.get_item(1).as_double(),
                    normal_data.get_item(2).as_double(),
                };
                dst_vertex.normal_ = glm::normalize(dst_vertex.normal_);

                // Joints
                auto group_iter = obj_mesh.get_attr("vertices").get_item(vertex_index).get_attr("groups").get_iter();
                while (true) {
                    auto g = group_iter.iter_next();
                    if (!g.is_ready())
                        break;

                    auto joint_name = bpy_mesh.get_attr("vertex_groups").get_item(g.get_attr("group")).get_attr("name").as_str();
                    auto joint_index = joint_index_map.get(joint_name);
                    if (joint_index) {
                        dst_vertex.add_joint(*joint_index, g.get_attr("weight").as_double());
                    }
                }
            }
        }
    }


    struct MeshRecord {
        b3dsung::Mesh mesh_;
        b3dsung::json_class json_data_;
        std::future<void> future_;

        ::PythonObject bpy_mesh;
        ::JointIndexMap joint_index_map_;
        std::string skeleton_name_;

        void parse_mesh() {
            ::parse_mesh(mesh_, bpy_mesh, skeleton_name_, joint_index_map_);
        }

        void build_flat() {
            mesh_.build_flat();
        }
    };


    void do_one_mesh(::MeshRecord* m) {
        m->build_flat();
    }


    class AsyncMeshManager {

    private:
        std::list<MeshRecord> data_;

    public:
        // Returns mesh name as a str
        std::string add_mesh(PyObject* bpy_mesh_ptr, ::PythonObject skeleton_name, const JointIndexMap& joint_index_map) {
            Py_INCREF(bpy_mesh_ptr);
            auto bpy_mesh = ::PythonObject{bpy_mesh_ptr, true};

            const auto mesh_name_obj = bpy_mesh.get_attr("data").get_attr("name");
            const auto mesh_name = mesh_name_obj.as_str();

            auto found = this->find_record_by_name(mesh_name.c_str());
            if (found != nullptr) {
                return found->mesh_.name_;
            }
            else {
                auto& added = this->data_.emplace_back();
                added.mesh_.name_ = mesh_name;
                added.joint_index_map_ = joint_index_map;
                added.skeleton_name_ = skeleton_name.as_str();
                added.bpy_mesh = std::move(bpy_mesh);
                added.parse_mesh();
                added.future_ = std::async(do_one_mesh, &added);
                return added.mesh_.name_;
            }
        }

        b3dsung::json_class make_json(b3dsung::BinaryBuilder& bin_array) {
            auto output = b3dsung::json_class::array();
            for (auto& mesh : this->data_) {
                mesh.future_.wait();
                mesh.mesh_.make_json(output, bin_array);
            }
            return output;
        }

        b3dsung::Mesh* find_by_name(const char* const name) {
            for (auto& mesh : this->data_) {
                if (mesh.mesh_.name_ == name) {
                    mesh.future_.wait();
                    return &mesh.mesh_;
                }
            }
            return nullptr;
        }

    private:
        MeshRecord* find_record_by_name(const char* const mesh_name) {
            for (auto& x : this->data_) {
                if (x.mesh_.name_ == mesh_name) {
                    return &x;
                }
            }
            return nullptr;
        }

    };

}


// Type: MeshManager
namespace {
namespace MeshManager {

    using ClassDef = ::AsyncMeshManager;


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

    PyObject* get_mesh_mat_pairs(ObjectDef* const self, PyObject* const args) {
        const char* mesh_name = nullptr;
        if (!PyArg_ParseTuple(args, "s", &mesh_name))
            return nullptr;

        auto mesh = self->impl_.find_by_name(mesh_name);
        auto output = PyList_New(0);

        for (auto& [material_name, vert_buf] : mesh->vertex_buffers_) {
            auto tuple = Py_BuildValue("(ss)", mesh->get_mangled_name(material_name.c_str()).c_str(), material_name.c_str());
            PyList_Append(output, tuple);
        }

        return output;
    }

    PyObject* add_bpy_mesh(ObjectDef* const self, PyObject* const args) try {
        ::PythonObject bpy_mesh;
        const char* skeleton_name = nullptr;
        ::PythonObject joint_name_index_map;
        if (!PyArg_ParseTuple(args, "OsO", bpy_mesh.out_ptr(), &skeleton_name, joint_name_index_map.out_ptr()))
            return nullptr;

        // Joint index map
        ::JointIndexMap joint_index_map;
        {
            if (!PyDict_Check(*joint_name_index_map))
                return nullptr;

            const auto keys = PyDict_Keys(*joint_name_index_map);
            const auto key_count = PyList_Size(keys);

            for (Py_ssize_t i = 0; i < key_count; ++i) {
                const auto key = PyList_GetItem(keys, i);
                if (!PyUnicode_Check(key))
                    return nullptr;

                const auto value = PyDict_GetItem(*joint_name_index_map, key);
                if (!PyLong_Check(value))
                    return nullptr;

                joint_index_map.set(
                    PyUnicode_AsUTF8(key),
                    PyLong_AsLong(value)
                );
            }
        }

        const auto mesh_name = self->impl_.add_mesh(*bpy_mesh, skeleton_name, joint_index_map);
        return PyUnicode_FromStringAndSize(mesh_name.c_str(), mesh_name.size());
    }
    catch (const std::runtime_error&) {
        return nullptr;
    }

    PyObject* make_json(ObjectDef* const self, PyObject* const args) {
        PyObject* bin_array_obj = nullptr;
        if (!PyArg_ParseTuple(args, "O", &bin_array_obj))
            return nullptr;

        if (!PyObject_IsInstance(bin_array_obj, (PyObject*)&::BinaryBuilder::type))
            return nullptr;

        auto bin_array = reinterpret_cast<::BinaryBuilder::ObjectDef*>(bin_array_obj);
        const auto json_data = self->impl_.make_json(bin_array->impl_);
        const auto json_str = json_data.dump();
        const auto json_str_obj = PyUnicode_FromStringAndSize(json_str.c_str(), json_str.size());

        auto json_module = PyImport_ImportModule("json");
        auto loads = PyObject_GetAttrString(json_module, "loads");
        auto py_json = PyObject_CallOneArg(loads, json_str_obj);
        return py_json;
    }

    std::vector<PyMethodDef> methods{
        {"get_mesh_mat_pairs", reinterpret_cast<PyCFunction>(get_mesh_mat_pairs), METH_VARARGS, ""},
        {"add_bpy_mesh", reinterpret_cast<PyCFunction>(add_bpy_mesh), METH_VARARGS, ""},
        {"make_json", reinterpret_cast<PyCFunction>(make_json), METH_VARARGS, ""},
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
