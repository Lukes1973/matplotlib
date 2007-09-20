import numpy as npy

class Path(object):
    # Path codes
    STOP      = 0 # 1 vertex
    MOVETO    = 1 # 1 vertex
    LINETO    = 2 # 1 vertex
    CURVE3    = 3 # 2 vertices
    CURVE4    = 4 # 3 vertices
    CLOSEPOLY = 5 # 1 vertex
    ###
    # MGDTODO: I'm not sure these are supported by PS/PDF/SVG,
    # so if they don't, we probably shouldn't
    CURVEN    = 6
    CATROM    = 7
    UBSPLINE  = 8
    ####

    NUM_VERTICES = [1, 1, 1, 2, 3, 1]
    
    code_type = npy.uint8
    
    def __init__(self, vertices, codes=None, closed=True):
        vertices = npy.asarray(vertices, npy.float_)
	assert vertices.ndim == 2
	assert vertices.shape[1] == 2
        
	if codes is None:
	    if closed:
		codes = self.LINETO * npy.ones(
		    vertices.shape[0] + 1, self.code_type)
		codes[0] = self.MOVETO
                codes[-1] = self.CLOSEPOLY
                vertices = npy.concatenate((vertices, [[0.0, 0.0]]))
	    else:
		codes = self.LINETO * npy.ones(
		    vertices.shape[0], self.code_type)
		codes[0] = self.MOVETO
        else:
	    codes = npy.asarray(codes, self.code_type)
            assert codes.ndim == 1
            assert len(codes) == len(vertices)

        self._codes = codes
	self._vertices = vertices
        
	assert self._codes.ndim == 1

    def __repr__(self):
	return "Path(%s, %s)" % (self.vertices, self.codes)
	    
    def _get_codes(self):
	return self._codes
    codes = property(_get_codes)

    def _get_vertices(self):
	return self._vertices
    vertices = property(_get_vertices)

    def iter_endpoints(self):
	i = 0
	NUM_VERTICES = self.NUM_VERTICES
	vertices = self.vertices
	for code in self.codes:
            if code == self.CLOSEPOLY:
                i += 1
            else:
                num_vertices = NUM_VERTICES[code]
                i += num_vertices - 1
                yield vertices[i]
                i += 1

    def transformed(self, transform):
        return Path(transform.transform(self.vertices), self.codes)

    def transformed_without_affine(self, transform):
        vertices, affine = transform.transform_without_affine(self.vertices)
        return Path(vertices, self.codes), affine
                
    _unit_rectangle = None
    #@classmethod
    def unit_rectangle(cls):
	if cls._unit_rectangle is None:
	    cls._unit_rectangle = \
		Path([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
	return cls._unit_rectangle
    unit_rectangle = classmethod(unit_rectangle)

    _unit_regular_polygons = {}
    #@classmethod
    def unit_regular_polygon(cls, numVertices):
	path = cls._unit_regular_polygons.get(numVertices)
	if path is None:
	    theta = 2*npy.pi/numVertices * npy.arange(numVertices)
	    # This is to make sure the polygon always "points-up"
	    theta += npy.pi / 2.0
	    verts = npy.vstack((npy.cos(theta), npy.sin(theta))).transpose()
	    path = Path(verts)
	    cls._unit_regular_polygons[numVertices] = path
	return path
    unit_regular_polygon = classmethod(unit_regular_polygon)

    _unit_circle = None
    #@classmethod
    def unit_circle(cls):
	# MGDTODO: Optimize?
	if cls._unit_circle is None:
	    offset = 4.0 * (npy.sqrt(2) - 1) / 3.0
	    vertices = npy.array(
		[[-1.0, 0.0],
		 
		 [-1.0, offset],
		 [-offset, 1.0],
		 [0.0, 1.0],
		 
		 [offset, 1.0],
		 [1.0, offset],
		 [1.0, 0.0],
		 
		 [1.0, -offset],
		 [offset, -1.0],
		 [0.0, -1.0],
		 
		 [-offset, -1.0],
		 [-1.0, -offset],
		 [-1.0, 0.0],

                 [-1.0, 0.0]],
                npy.float_)

            codes = cls.CURVE4 + npy.ones((len(vertices)))
	    codes[0] = cls.MOVETO
            codes[-1] = cls.CLOSEPOLY

	    cls._unit_circle = Path(vertices, codes)
	return cls._unit_circle
    unit_circle = classmethod(unit_circle)

# MGDTODO: Add a transformed path that would automatically invalidate
# itself when its transform changes
