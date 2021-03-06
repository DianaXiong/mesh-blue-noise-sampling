import sys
import numpy
import argparse

from scipy.spatial.distance import pdist, squareform
from scipy.spatial import KDTree

import stlparser

import matplotlib.pyplot as plot
from mpl_toolkits.mplot3d import Axes3D



def mesh_area(triangle_list):
	N = numpy.cross(triangle_list[:,1] - triangle_list[:,0], triangle_list[:,2] - triangle_list[:,0], axis = 1)
	N_norm = numpy.sqrt(numpy.sum(N ** 2, axis = 1))
	N_norm *= .5
	return N_norm



reflection = numpy.array([[0., -1.], [-1., 0.]])

def triangle_point_picking(triangle_list):
	# Compute uniform distribution over [0, 1]x[0, 1] lower triangle
	X = numpy.random.random((triangle_list.shape[0], 2))
	t = numpy.sum(X, axis = 1) > 1
	X[t] = numpy.dot(X[t], reflection) + 1.

	# Map the [0, 1]x[0, 1] lower triangle to the actual triangles
	ret = numpy.einsum('ijk,ij->ik', triangle_list[:,1:] - triangle_list[:,0,None], X) 
	ret += triangle_list[:,0]
	return ret



def uniform_sample_mesh(triangle_list, triangle_area_list, sample_count):
	# Normalize the sum of area of each triangle to 1
	triangle_area = triangle_area_list / numpy.sum(triangle_area_list)

	'''
	For each sample
	  * Pick a triangle with probability proportial to its surface area
	  * pick a point on that triangle with uniform probability
	'''

	triangle_id_list = numpy.random.choice(triangle_list.shape[0], size = sample_count, p = triangle_area)
	return triangle_point_picking(triangle_list[triangle_id_list])



def blue_noise_sample_elimination(point_list, mesh_surface_area, sample_count):
	# Parameters
	alpha = 8
	rmax = numpy.sqrt(mesh_surface_area / ((2 * sample_count) * numpy.sqrt(3.))) 

	# Compute a KD-tree of the input point list
	kdtree = KDTree(point_list)

	# Compute the weight for each sample
	D = numpy.minimum(squareform(pdist(point_list)), 2 * rmax)
	D = (1. - (D / (2 * rmax))) ** alpha

	W = numpy.zeros(point_list.shape[0])
	for i in range(point_list.shape[0]):
		W[i] = sum(D[i, j] for j in kdtree.query_ball_point(point_list[i], 2 * rmax) if i != j)

	# Pick the samples we need
	heap = sorted((w, i) for i, w in enumerate(W))

	id_set = set(range(point_list.shape[0]))
	while len(id_set) > sample_count:
		# Pick the sample with the highest weight
		w, i = heap.pop()
		id_set.remove(i)

		neighbor_set = set(kdtree.query_ball_point(point_list[i], 2 * rmax))
		neighbor_set.remove(i)
		heap = [(w - D[i, j], j) if j in neighbor_set else (w, j) for w, j in heap]				
		heap.sort()

	# Job done
	return point_list[sorted(id_set)]



def main():
	# Command line parsing
	parser = argparse.ArgumentParser(description = 'Compute and show a blue noise sampling of a triangul mesh')
	parser.add_argument('-n', '--sample-count', type = int, default = 2048, help = 'number of sample to compute')
	args = parser.parse_args()

	# Load the input mesh as a list of triplets (ie. triangles) of 3d vertices
	try:
		triangle_list = numpy.array([X for X, N in stlparser.load(sys.stdin)])
	except stlparser.ParseError as e:
		sys.stderr.write('%s\n' % e)
		sys.exit(0)

	# Compute surface area of each triangle
	tri_area = mesh_area(triangle_list)

	# Compute an uniform sampling of the input mesh
	point_list = uniform_sample_mesh(triangle_list, tri_area, 4 * args.sample_count)

	# Compute a blue noise sampling of the input mesh, seeded by the previous sampling
	point_list = blue_noise_sample_elimination(point_list, numpy.sum(tri_area), args.sample_count)

	# Display
	fig = plot.figure()
	ax = fig.gca(projection = '3d')
	ax._axis3don = False
	ax.set_aspect('equal')
	ax.scatter(point_list[:,0], point_list[:,1], point_list[:,2], lw = 0., c = 'k')
	plot.show()
	


if __name__ == '__main__':
	main()
