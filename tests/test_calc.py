from core.tools import safe_calc


def test_basic_math():
    assert safe_calc("23*(5+2)") == "161"
    assert safe_calc("-3 + 10 // 3") == "0"
    assert safe_calc("2**10") == "1024"


def test_rejects_code():
    for bad in ["__import__('os').system('id')", "open('x')", "abs(1)", "a+1", "'a'*3", "True+1"]:
        assert safe_calc(bad).startswith("calc error")


def test_pow_and_size_limits():
    assert "exponent too large" in safe_calc("9**9**9")
    assert "too large" in safe_calc("10**999")
    assert "too long" in safe_calc("1+" * 200 + "1")


def test_division_by_zero():
    assert safe_calc("1/0") == "calc error: division by zero"
