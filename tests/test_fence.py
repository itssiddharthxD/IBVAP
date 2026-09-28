from security_engine.virtual_fence import point_in_polygon

def test_inside():
    assert point_in_polygon((5,5), [(0,0),(10,0),(10,10),(0,10)])

def test_outside():
    assert not point_in_polygon((20,20), [(0,0),(10,0),(10,10),(0,10)])
