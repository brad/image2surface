#!/usr/bin/python
# -*- coding: utf-8 -*-
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
	parser.add_argument('-o', dest='filename', type=str, default='image2surface.dat', help='By default, this script just outputs textsurface.dat, which can be imported into an OpenSCAD document. If you specify a .scad filename for this parameter, the script will also output a .scad file which imports the surface. If you specify a .stl filename, the script will go further and generate a .stl file.')
	return parser.parse_args()

def get_image_data(imagefile):
	im = Image.open(imagefile)
	return [list(im.getdata()), im.size[0], im.size[1]]

def create_dat(data, zheight, filename, inverse):
	white = 255*len(data[0])
	textbuffer = ''
	line = []
	lines = []
	for i in range(len(data)):
		if i%width == 0 and i != 0:
			line.reverse()
			lines.append(line)
			line = []
		line.append(data[i])

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

def create_scad(datfilename, filename, removebase, width, height, maxdim):
	if width > height:
		scale = [float(maxdim)/width, (maxdim*float(height)/width)/height, 1]
	else:
		scale = [(maxdim*float(width)/height)/width, float(maxdim)/height, 1]
	scadfilename = filename if filename[-5:] == '.scad' else 'temp_image2surface.scad'
	baseheight = 2
	f = open(scadfilename, 'w')
	if removebase:
		f.write('translate([0, 0, -baseheight]);\ndifference() {\n\t')
	f.write('scale('+repr(scale)+') translate([0, 0, 1]) surface("'+datfilename+'", center=true, convexity=5);')
	if removebase:
		f.write('\n\tcube(['+repr(scale[0]*width)+', '+repr(scale[1]*height)+', baseheight], center=true);\n}')
	f.close()
	print 'SCAD file is '+scadfilename
	return scadfilename

def create_stl(filename, scadfilename):
	openscadexec = 'openscad'
	windows = 'C:\Program Files\OpenSCAD\openscad.exe'
	mac = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'
	if os.path.exists(windows):
		openscadexec = windows
	elif os.path.exists(mac):
		openscadexec = mac
	stlfilename = filename
	command = [openscadexec, '-m', 'make', '-s', filename, scadfilename]
	print 'Exporting to STL'
	subprocess.call(command)
	print 'STL file is '+stlfilename

if __name__ == '__main__':
	args = get_args()

	# Generates an RGBA array, given an image file
	[data, width, height] = get_image_data(args.imagefile)

	# Outputs a .dat file that OpenSCAD can use with the surface command
	datfilename = create_dat(data, args.zheight, args.filename, args.inverse)

	# Generate .scad and/or .stl
	if args.filename[-5:] == '.scad' or args.filename[-4:] == '.stl':
		# Outputs a .scad file that can be used to create a .stl file
		scadfilename = create_scad(datfilename, args.filename, args.removebase, width, height, args.maxdim)
		if args.filename[-4:] == '.stl':
			# Outputs a printable .stl file
			create_stl(args.filename, scadfilename)
