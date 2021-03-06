import numpy as np
import mdtraj as md
import matplotlib as mpl
font = {'family' : 'normal','weight' : 'normal','size'   : 15}
mpl.rc('font', **font)
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

"""
def compute_phipsi(struc): dihedrals
def rama(dihedrals,outdir,name_mod): None
def plot_struc_rama(struc,name,dihedrals,outdir,name_mod): None
"""

def compute_phipsi(struc):
	"""
	compute dihedrals for Ramachandran plot

	"""
	phi = md.compute_phi(struc)[1][0]
	psi = md.compute_psi(struc)[1][0]
	dihedrals = np.array([phi,psi]).T
	return dihedrals

def rama(dihedrals,outdir,name_mod):
	"""
	Compute Ramachandran angles

	"""
	dihedrals = np.array(dihedrals)
	a,b,c = dihedrals.shape
	angles = dihedrals.reshape(a*b,c).T

	fig, ax = plt.subplots()
	plot = plt.hist2d(angles[0], angles[1], bins = 30, norm=LogNorm(), cmap='hot')
	ax.set_xlabel("phi")
	ax.set_ylabel("psi")
	cbar = plt.colorbar()
	cbar.set_label("number of occurances")
	#plt.show()
	plt.savefig(outdir+"RAMA" + name_mod + ".png")
	np.savetxt(outdir+"RAMA_all" + name_mod + ".npy",angles)
	return None

def plot_struc_rama(struc,name,dihedrals,outdir,name_mod):
	"""
	Make Ramachandran heatmap

	"""
	di = np.array(compute_phipsi(struc))
	dihedrals = np.array(dihedrals)

	fig, ax = plt.subplots()
	plot = plt.hist2d(dihedrals[0], dihedrals[1], bins = 30, norm=LogNorm(), cmap='hot')
	ax.set_xlabel("phi")
	ax.set_ylabel("psi")
	cbar = plt.colorbar()
	cbar.set_label("number of occurances")
	for i, txt in enumerate(range(1,len(di.T[0]))):
		ax.annotate(txt, (di.T[0][i],di.T[1][i]))
	plt.scatter(di.T[0], di.T[1], c='k', s=20)
	plt.savefig(outdir+'RAMA_'+name.split('/')[1] + name_mod + ".png")
	return None

