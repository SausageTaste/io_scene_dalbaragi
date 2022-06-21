#pragma once

#define PY_SSIZE_T_CLEAN


#ifdef _DEBUG
    #define _STL_CRT_SECURE_INVALID_PARAMETER(expr) _CRT_SECURE_INVALID_PARAMETER(expr)
    #undef _DEBUG
    #include <python.h>
    #include <structmember.h>
    #define _DEBUG
#else
    #include <python.h>
    #include <structmember.h>
#endif
