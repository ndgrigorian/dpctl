import itertools

import numpy as np
import pytest

import dpctl
import dpctl.tensor as dpt
from dpctl.tests.helper import get_queue_or_skip, skip_if_dtype_not_supported

_all_dtypes = [
    "b1",
    "i1",
    "u1",
    "i2",
    "u2",
    "i4",
    "u4",
    "i8",
    "u8",
    "f2",
    "f4",
    "f8",
    "c8",
    "c16",
]
_usm_types = ["device", "shared", "host"]


@pytest.mark.parametrize("dtype", _all_dtypes)
def test_abs_out_type(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    arg_dt = np.dtype(dtype)
    X = dpt.asarray(0, dtype=arg_dt, sycl_queue=q)
    if np.issubdtype(arg_dt, np.complexfloating):
        type_map = {
            np.dtype("c8"): np.dtype("f4"),
            np.dtype("c16"): np.dtype("f8"),
        }
        assert dpt.abs(X).dtype == type_map[arg_dt]
    else:
        assert dpt.abs(X).dtype == arg_dt


@pytest.mark.parametrize("usm_type", _usm_types)
def test_abs_usm_type(usm_type):
    q = get_queue_or_skip()

    arg_dt = np.dtype("i4")
    input_shape = (10, 10, 10, 10)
    X = dpt.empty(input_shape, dtype=arg_dt, usm_type=usm_type, sycl_queue=q)
    X[..., 0::2] = 1
    X[..., 1::2] = 0

    Y = dpt.abs(X)
    assert Y.usm_type == X.usm_type
    assert Y.sycl_queue == X.sycl_queue
    assert Y.flags.c_contiguous

    expected_Y = dpt.asnumpy(X)
    assert np.allclose(dpt.asnumpy(Y), expected_Y)


@pytest.mark.parametrize("dtype", _all_dtypes[1:])
def test_abs_order(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    arg_dt = np.dtype(dtype)
    input_shape = (10, 10, 10, 10)
    X = dpt.empty(input_shape, dtype=arg_dt, sycl_queue=q)
    X[..., 0::2] = 1
    X[..., 1::2] = 0

    for ord in ["C", "F", "A", "K"]:
        for perms in itertools.permutations(range(4)):
            U = dpt.permute_dims(X[:, ::-1, ::-1, :], perms)
            Y = dpt.abs(U, order=ord)
            expected_Y = np.ones(Y.shape, dtype=Y.dtype)
            expected_Y[..., 1::2] = 0
            expected_Y = np.transpose(expected_Y, perms)
            assert np.allclose(dpt.asnumpy(Y), expected_Y)


@pytest.mark.parametrize("dtype", ["c8", "c16"])
def test_abs_complex(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    arg_dt = np.dtype(dtype)
    input_shape = (10, 10, 10, 10)
    X = dpt.empty(input_shape, dtype=arg_dt, sycl_queue=q)
    Xnp = np.random.standard_normal(
        size=input_shape
    ) + 1j * np.random.standard_normal(size=input_shape)
    Xnp = Xnp.astype(arg_dt)
    X[...] = Xnp

    for ord in ["C", "F", "A", "K"]:
        for perms in itertools.permutations(range(4)):
            U = dpt.permute_dims(X[:, ::-1, ::-1, :], perms)
            Y = dpt.abs(U, order=ord)
            expected_Y = np.abs(np.transpose(Xnp[:, ::-1, ::-1, :], perms))
            tol = dpt.finfo(Y.dtype).resolution
            np.testing.assert_allclose(
                dpt.asnumpy(Y), expected_Y, atol=tol, rtol=tol
            )


def _compare_dtypes(dt, ref_dt, sycl_queue=None):
    assert isinstance(sycl_queue, dpctl.SyclQueue)
    dev = sycl_queue.sycl_device
    expected_dt = ref_dt
    if not dev.has_aspect_fp64:
        if expected_dt == dpt.float64:
            expected_dt = dpt.float32
        elif expected_dt == dpt.complex128:
            expected_dt = dpt.complex64
    if not dev.has_aspect_fp16:
        if expected_dt == dpt.float16:
            expected_dt = dpt.float32
    return dt == expected_dt


@pytest.mark.parametrize("op1_dtype", _all_dtypes)
@pytest.mark.parametrize("op2_dtype", _all_dtypes)
def test_add_dtype_matrix(op1_dtype, op2_dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(op1_dtype, q)
    skip_if_dtype_not_supported(op2_dtype, q)

    sz = 127
    ar1 = dpt.ones(sz, dtype=op1_dtype)
    ar2 = dpt.ones_like(ar1, dtype=op2_dtype)

    r = dpt.add(ar1, ar2)
    assert isinstance(r, dpt.usm_ndarray)
    expected_dtype = np.add(
        np.zeros(1, dtype=op1_dtype), np.zeros(1, dtype=op2_dtype)
    ).dtype
    assert _compare_dtypes(r.dtype, expected_dtype, sycl_queue=q)
    assert r.shape == ar1.shape
    assert (dpt.asnumpy(r) == np.full(r.shape, 2, dtype=r.dtype)).all()
    assert r.sycl_queue == ar1.sycl_queue

    ar3 = dpt.ones(sz, dtype=op1_dtype)
    ar4 = dpt.ones(2 * sz, dtype=op2_dtype)

    r = dpt.add(ar3[::-1], ar4[::2])
    assert isinstance(r, dpt.usm_ndarray)
    expected_dtype = np.add(
        np.zeros(1, dtype=op1_dtype), np.zeros(1, dtype=op2_dtype)
    ).dtype
    assert _compare_dtypes(r.dtype, expected_dtype, sycl_queue=q)
    assert r.shape == ar3.shape
    assert (dpt.asnumpy(r) == np.full(r.shape, 2, dtype=r.dtype)).all()


@pytest.mark.parametrize("op1_usm_type", _usm_types)
@pytest.mark.parametrize("op2_usm_type", _usm_types)
def test_add_usm_type_matrix(op1_usm_type, op2_usm_type):
    get_queue_or_skip()

    sz = 128
    ar1 = dpt.ones(sz, dtype="i4", usm_type=op1_usm_type)
    ar2 = dpt.ones_like(ar1, dtype="i4", usm_type=op2_usm_type)

    r = dpt.add(ar1, ar2)
    assert isinstance(r, dpt.usm_ndarray)
    expected_usm_type = dpctl.utils.get_coerced_usm_type(
        (op1_usm_type, op2_usm_type)
    )
    assert r.usm_type == expected_usm_type


def test_add_order():
    get_queue_or_skip()

    ar1 = dpt.ones((20, 20), dtype="i4", order="C")
    ar2 = dpt.ones((20, 20), dtype="i4", order="C")
    r1 = dpt.add(ar1, ar2, order="C")
    assert r1.flags.c_contiguous
    r2 = dpt.add(ar1, ar2, order="F")
    assert r2.flags.f_contiguous
    r3 = dpt.add(ar1, ar2, order="A")
    assert r3.flags.c_contiguous
    r4 = dpt.add(ar1, ar2, order="K")
    assert r4.flags.c_contiguous

    ar1 = dpt.ones((20, 20), dtype="i4", order="F")
    ar2 = dpt.ones((20, 20), dtype="i4", order="F")
    r1 = dpt.add(ar1, ar2, order="C")
    assert r1.flags.c_contiguous
    r2 = dpt.add(ar1, ar2, order="F")
    assert r2.flags.f_contiguous
    r3 = dpt.add(ar1, ar2, order="A")
    assert r3.flags.f_contiguous
    r4 = dpt.add(ar1, ar2, order="K")
    assert r4.flags.f_contiguous

    ar1 = dpt.ones((40, 40), dtype="i4", order="C")[:20, ::-2]
    ar2 = dpt.ones((40, 40), dtype="i4", order="C")[:20, ::-2]
    r4 = dpt.add(ar1, ar2, order="K")
    assert r4.strides == (20, -1)

    ar1 = dpt.ones((40, 40), dtype="i4", order="C")[:20, ::-2].mT
    ar2 = dpt.ones((40, 40), dtype="i4", order="C")[:20, ::-2].mT
    r4 = dpt.add(ar1, ar2, order="K")
    assert r4.strides == (-1, 20)


def test_add_broadcasting():
    get_queue_or_skip()

    m = dpt.ones((100, 5), dtype="i4")
    v = dpt.arange(5, dtype="i4")

    r = dpt.add(m, v)

    assert (dpt.asnumpy(r) == np.arange(1, 6, dtype="i4")[np.newaxis, :]).all()

    r2 = dpt.add(v, m)
    assert (dpt.asnumpy(r2) == np.arange(1, 6, dtype="i4")[np.newaxis, :]).all()


def _map_to_device_dtype(dt, dev):
    if np.issubdtype(dt, np.integer):
        return dt
    if np.issubdtype(dt, np.floating):
        dtc = np.dtype(dt).char
        if dtc == "d":
            return dt if dev.has_aspect_fp64 else dpt.float32
        elif dtc == "e":
            return dt if dev.has_aspect_fp16 else dpt.float32
        return dt
    if np.issubdtype(dt, np.complexfloating):
        dtc = np.dtype(dt).char
        if dtc == "D":
            return dt if dev.has_aspect_fp64 else dpt.complex64
        return dt
    return dt


@pytest.mark.parametrize("dtype", _all_dtypes)
def test_cos_out_type(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    X = dpt.asarray(0, dtype=dtype, sycl_queue=q)
    expected_dtype = np.cos(np.array(0, dtype=dtype)).dtype
    expected_dtype = _map_to_device_dtype(expected_dtype, q.sycl_device)
    assert dpt.cos(X).dtype == expected_dtype


@pytest.mark.parametrize("dtype", ["f2", "f4", "f8", "c8", "c16"])
def test_cos_output(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    n_seq = 100
    n_rep = 137

    Xnp = np.linspace(-np.pi / 4, np.pi / 4, num=n_seq, dtype=dtype)
    X = dpt.asarray(np.repeat(Xnp, n_rep), dtype=dtype, sycl_queue=q)

    Y = dpt.cos(X)
    tol = 8 * dpt.finfo(Y.dtype).resolution

    np.testing.assert_allclose(
        dpt.asnumpy(Y), np.repeat(np.cos(Xnp), n_rep), atol=tol, rtol=tol
    )


@pytest.mark.parametrize("usm_type", ["device", "shared", "host"])
def test_cos_usm_type(usm_type):
    q = get_queue_or_skip()

    arg_dt = np.dtype("f4")
    input_shape = (10, 10, 10, 10)
    X = dpt.empty(input_shape, dtype=arg_dt, usm_type=usm_type, sycl_queue=q)
    X[..., 0::2] = np.pi / 6
    X[..., 1::2] = np.pi / 3

    Y = dpt.cos(X)
    assert Y.usm_type == X.usm_type
    assert Y.sycl_queue == X.sycl_queue
    assert Y.flags.c_contiguous

    expected_Y = np.empty(input_shape, dtype=arg_dt)
    expected_Y[..., 0::2] = np.cos(np.float32(np.pi / 6))
    expected_Y[..., 1::2] = np.cos(np.float32(np.pi / 3))
    assert np.allclose(dpt.asnumpy(Y), expected_Y)


@pytest.mark.parametrize("dtype", _all_dtypes)
def test_cos_order(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    arg_dt = np.dtype(dtype)
    input_shape = (10, 10, 10, 10)
    X = dpt.empty(input_shape, dtype=arg_dt, sycl_queue=q)
    X[..., 0::2] = np.pi / 6
    X[..., 1::2] = np.pi / 3

    for ord in ["C", "F", "A", "K"]:
        for perms in itertools.permutations(range(4)):
            U = dpt.permute_dims(X[:, ::-1, ::-1, :], perms)
            Y = dpt.cos(U, order=ord)
            expected_Y = np.cos(dpt.asnumpy(U))
            assert np.allclose(dpt.asnumpy(Y), expected_Y)


@pytest.mark.parametrize("dtype", _all_dtypes)
def test_isnan_out_type(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    X = dpt.asarray(0, dtype=dtype, sycl_queue=q)
    assert dpt.isnan(X).dtype == dpt.bool


def test_isnan_output():
    q = get_queue_or_skip()

    Xnp = np.asarray(np.nan)
    X = dpt.asarray(np.nan, sycl_queue=q)
    assert dpt.asnumpy(dpt.isnan(X))[()] == np.isnan(Xnp)


@pytest.mark.parametrize("dtype", ["c8", "c16"])
def test_isnan_complex(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    y1 = complex(np.nan, np.nan)
    y2 = complex(1, np.nan)
    y3 = complex(np.nan, 1)
    y4 = complex(2, 1)
    y5 = complex(np.inf, 1)

    Ynp = np.repeat(np.array([y1, y2, y3, y4, y5], dtype=dtype), 123)
    Y = dpt.asarray(Ynp, sycl_queue=q)
    assert np.array_equal(dpt.asnumpy(dpt.isnan(Y))[()], np.isnan(Ynp))


@pytest.mark.parametrize("dtype", ["f2", "f4", "f8"])
def test_isnan_floats(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    y1 = np.nan
    y2 = 1
    y3 = np.inf

    for mult in [123, 137, 255, 271, 272]:
        Ynp = np.repeat(np.array([y1, y2, y3], dtype=dtype), mult)
        Y = dpt.asarray(Ynp, sycl_queue=q)
        assert np.array_equal(dpt.asnumpy(dpt.isnan(Y))[()], np.isnan(Ynp))


@pytest.mark.parametrize("dtype", _all_dtypes)
def test_isnan_order(dtype):
    q = get_queue_or_skip()
    skip_if_dtype_not_supported(dtype, q)

    arg_dt = np.dtype(dtype)
    input_shape = (10, 10, 10, 10)
    X = dpt.ones(input_shape, dtype=arg_dt, sycl_queue=q)

    for ord in ["C", "F", "A", "K"]:
        for perms in itertools.permutations(range(4)):
            U = dpt.permute_dims(X[::2, ::-1, ::-1, ::5], perms)
            Y = dpt.isnan(U, order=ord)
            expected_Y = np.full(Y.shape, False, dtype=Y.dtype)
            assert np.allclose(dpt.asnumpy(Y), expected_Y)
