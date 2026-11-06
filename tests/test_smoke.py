import lasagna


def test_package_imports_and_declares_its_versions():
    assert isinstance(lasagna.__version__, str)
    assert isinstance(lasagna.PROTOCOL_VERSION, str)
