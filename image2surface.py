#!/usr/bin/python
# -*- coding: utf-8 -*-
u"""
Copyright (C) 2011 Brad Pitcher, bradpitcher@gmail.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from argparse import ArgumentParser
from PIL import Image
import os
import subprocess

def get_args():
	parser = ArgumentParser(description='Convert image to a surface for OpenSCAD and a .stl if desired.')
	parser.add_argument('imagefile', metavar='IMAGEFILE', type=str, help='The path to the image file you want to convert to a surface.')
	parser.add_argument('-i', dest='inverse', action='store_const', const=True, default=False, help='Defaults to white as a background, this option makes black the background.')
	parser.add_argument('-r', dest='removebase', action='store_const', const=True, default=False, help='Remove base layer from surface. Only applies if exporting to .scad and/or .stl.')
	parser.add_argument('-d', dest='maxdim', type=int, default=150, help='The maximum size in mm to make the x or y dimension. Only applies if exporting to .scad and/or .stl.')
	parser.add_argument('-z', dest='zheight', type=int, default=5, help='The max z-height of the text, defaults to 5')
	parser.add_argument('-o', dest='filename', type=str, default='image2surface.dat', help='By default, this script just outputs textsurface.dat, which can be imported into an OpenSCAD document. If you specify a .scad filename for this parameter, the script will also output a .scad file which imports the surface. If you specify a .stl filename, the script will go further and generate a .stl file. If you specify a .dxf filename, the script will create a .dxf')
	return parser.parse_args()

def get_openscad_exec():
	openscadexec = 'openscad'
	windows = 'C:\Program Files\OpenSCAD\openscad.exe'
	mac = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
	if os.path.exists(windows):
		openscadexec = windows
	elif os.path.exists(mac):
		openscadexec = mac
	return openscadexec

def get_image_data(imagefile):
	im = Image.open(imagefile)
	return [list(im.getdata()), im.size[0], im.size[1]]

def create_dat(data, zheight, filename, inverse):
	dxf = (filename[-4:] == '.dxf')
	white = 255*len(data[0])
	textbuffer = ''
	line = []
	lines = []
	for i in range(len(data)):
		if i%width == 0 and i != 0:
			if not dxf:
				line.reverse()
			lines.append(line)
			line = []
		if dxf:
			line.append(0 if sum(data[i]) == white else 1)
		else:
			line.append(data[i])

	if dxf:
		print 'Created matrix'
		return lines
	else:
		# To data
		for line in lines:
			textbuffer += '\n'
			for pixel in line:
				ratio = float(sum(pixel))/white
				if not inverse:
					ratio = 1-ratio			
				# Numbers (with decimal places) must be reversed so
				# that when the entire textbuffer is reversed later,
				# numbers will be correct
				textbuffer += (' '+repr(ratio*zheight))[::-1]

		datfilename = filename if filename[-4:] == '.dat' else 'temp_image2surface.dat'
		f = open(datfilename, 'w')
		f.write(textbuffer[::-1])
		f.close()	
		print 'Surface is in '+datfilename
		return datfilename

def create_scad(dat, filename, removebase, width, height, maxdim):
	dxf = (filename[-4:] == '.dxf')
	print 'Creating SCAD file'
	if width > height:
		scale = [float(maxdim)/width, (maxdim*float(height)/width)/height, 1]
	else:
		scale = [(maxdim*float(width)/height)/width, float(maxdim)/height, 1]
	scadfilename = filename if filename[-5:] == '.scad' else 'temp_image2surface.scad'
	f = open(scadfilename, 'w')
	if dxf:
		f.write("""
	2d = %s;
	fudge = 0.01;
	block_z = %i;
	block_size = 2;
	matrix_rows = %i;
	matrix_cols = %i;
	""" % ('true' if dxf else 'false', 0, len(dat), len(dat[0])))
		# Format the matrix nicely
		f.write('\nmatrix = [\n')
		for line in dat:
			f.write('%s,\n' % (repr(line)))
		f.write('];')
		f.write(display_matrix_core(scale))
	else:
		if removebase:
			f.write('translate([0, 0, -1]) difference() {\n\t')
		f.write('scale('+repr(scale)+') translate([0, 0, 1]) surface("'+dat+'", center=true, convexity=5);')
		if removebase:
			f.write('\n\ttranslate([-0.1, 0, 0]) cube(['+repr(scale[0]*width)+', '+repr(scale[1]*height)+', 2.1], center=true);\n}')
	f.close()
	print 'SCAD file is '+scadfilename
	return scadfilename

def create_stl(filename, scadfilename):
	openscadexec = get_openscad_exec()
	stlfilename = filename
	command = [openscadexec, '-m', 'make', '-s', filename, scadfilename]
	print 'Exporting to STL'
	subprocess.call(command)
	print 'STL file is '+stlfilename

def create_dxf(filename, scadfilename):
	openscadexec = get_openscad_exec()
	dxffilename = filename
	command = [openscadexec, '-m', 'make', '-x', filename, scadfilename]
	print 'Exporting to DXF'
	subprocess.call(command)
	print 'DXF file is '+dxffilename

def display_matrix_core(scale):
	return """
module block(bit, x, y, z, 2d) {
	if(2d) {
		square([x, y]);
	}
	else {
		cube([x, y, z*bit]);
	}	
}

scale(%s) translate([-block_size*matrix_cols/2, block_size*(matrix_rows/2-1), 0]) {
	if( ! 2d) {
		translate([0, -block_size*(matrix_rows-1), 0]) {
			cube([block_size*matrix_cols, block_size*matrix_rows, 1]);
		}
	}
	translate([0, 0, 1]) {
		for(i = [0 : matrix_rows-1]) {
			for(j = [0 : matrix_cols-1]) {
				if(matrix[i][j] != 0) {
					translate([block_size*j, -block_size*i, 0]) {
						if(i == 0 && j == matrix_cols-1) {
							// Draw the top right corner block normal size
							block(matrix[i][j], block_size, block_size, block_z, 2d);
						}
						else if(i == 0) {
							// Draw blocks on the top row with a x fudge factor added
							block(matrix[i][j], block_size+fudge, block_size, block_z, 2d);
						}
						else if(j == matrix_cols-1) {
							// Draw blocks on the right column with a y fudge factor added
							block(matrix[i][j], block_size, block_size+fudge, block_z, 2d);
						}
						else {
							// For blocks that aren't on the edge, add a fudge factor so they are connected to other blocks
							block(matrix[i][j], block_size+fudge, block_size+fudge, block_z, 2d);
						}
					}
				}
			}
		}
	}
}
""" % (repr(scale))

if __name__ == '__main__':
	args = get_args()

	# Generates an RGBA array, given an image file
	[data, width, height] = get_image_data(args.imagefile)

	# Outputs a .dat file that OpenSCAD can use with the surface command, or a matrix if .dxf output was specified
	dat = create_dat(data, args.zheight, args.filename, args.inverse)

	# Generate .scad and/or .stl
	if args.filename[-5:] == '.scad' or args.filename[-4:] == '.stl' or args.filename[-4:] == '.dxf':
		# Outputs a .scad file that can be used to create a .stl file
		scadfilename = create_scad(dat, args.filename, args.removebase, width, height, args.maxdim)
		if args.filename[-4:] == '.stl':
			# Outputs a printable .stl file
			create_stl(args.filename, scadfilename)
		elif args.filename[-4:] == '.dxf':
			create_dxf(args.filename, scadfilename)
