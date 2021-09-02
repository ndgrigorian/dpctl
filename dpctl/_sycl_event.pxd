#                      Data Parallel Control (dpctl)
#
# Copyright 2020-2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# distutils: language = c++
# cython: language_level=3

""" This file declares the SyclEvent extension type.
"""

from ._backend cimport DPCTLSyclEventRef


cdef public api class _SyclEvent [
    object Py_SyclEventObject,
    type Py_SyclEventType
]:
    """ Data owner for SyclEvent
    """
    cdef DPCTLSyclEventRef _event_ref
    cdef object args


cdef public api class SyclEvent(_SyclEvent) [
    object PySyclEventObject,
    type PySyclEventType
]:
    """ Python wrapper class for a ``cl::sycl::event``
    """
    @staticmethod
    cdef SyclEvent _create (DPCTLSyclEventRef event, object args=*)
    cdef int _init_event_default(self)
    cdef int _init_event_from__SyclEvent(self, _SyclEvent other)
    cdef int _init_event_from_capsule(self, object caps)
    cdef DPCTLSyclEventRef get_event_ref (self)
    cdef void _wait (SyclEvent event)
    cpdef void wait (self)