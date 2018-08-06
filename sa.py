import numpy as np
import mdtraj as md
import os
from IDP_analysis import polymer
from IDP_analysis import pca
from IDP_analysis import kmeans_clusters
from IDP_analysis import sa_core
from IDP_analysis import rama
from IDP_analysis import sa_traj
from IDP_analysis import mem

"""
			################################
			### Structure Analysis Class ###
			###        Dillion Fox       ###
			###          6/2018          ###
			###        UPenn/ORNL        ###
			################################

This class contains some functions that may be useful for analyzing protein structures
It can be run several different ways. First, an initial run will compute Rg, SASA, end-to-end distance,
asphericity, average secondary structure per residue, average contact maps, and the flory exponent.

Note that you can pick and choose the tasks you wish to run by specifying the "calcs" variable
upon instantiating the class.

The results can then be analyzed using PCA, which can take in any scalar quantities computed above
and sort them into 'PC' space. The points in PC space are then clustered using k-means. The centroids
of the k-means clusters should be meangingfully distinct, and the variance computed from PCA can tell you 
what distinguishes them.

The structural analyses can then be repeated for each cluster. Another script can be used to organize the
array of plots for each cluster to summarize the structural differences (I have a script that does this on
my github. Look for "rosetta_post.py".

The code can also read in a score.fsc file, which is a direct output file from Rosetta containing estimates
for how "good" each decoy structure is. If this file is read in, the structural analysis can be limited to
the top "N" structures.

This code can also try to fit end-to-end distributions to some fundamental polymer physics models, such
as Gaussian chains or semiflexible polymers.

An example of how I used this script to analyze Rosetta structures can be found at the bottom, under
the "if __name__ == "__main__:" line. Since the trajectories are read by MDTraj, this code is not limited
to dcd's, though some very simple task managing functions would have to be modified to read different 
formats. 

Finally, another script on my github account can be found that uses this class to sequentially analyze 
20 Monte Carlo trajectories of different sequences. See "campari_analyze.py" and "campari_post.py" for
ideas of how this can be used.

"""


class SA:

	def __init__(self, trajname, top='NULL', name_mod='', outdir='', calcs=[]):
		"""
		Create class objects. Keep most of them empty so they can be filled as the code progresses.

		"""
		self.trajname = trajname	# store name of trajectory
		self.top = top			# store topology (pdb, only needed if traj is compressed)
		self.name_mod = name_mod	# several functions are reused, so this name differentiates them
		self.EED = [] 			# end-to-end distance
		self.Rg = [] 			# radius of gyration
		self.XRg = [] 			# predicted x-ray radius of gyration (from crysol)
		self.SASA = [] 			# solvent accessible surface area
		self.Asph = [] 			# asphericity 
		self.SS = []			# secondary structure (per residue)
		self.cmaps = []			# contact maps
		self.gcmaps = []		# contact maps for specific residues
		self.scmaps = []		# contact maps for residues on surface only
		self.dihedrals = []		# store dihedrals to generate Ramachandran plot
		self.calcs = calcs		# list of calculations to perform at run time
		self.outdir = outdir		# directory to write output to
		self.fex = []			# Flory Exponent
		self.k = []			# k-means clusters labels
		self.B = []			# matrix in PC space
		self.scores = []		# list of scores from Rosetta with global index: [ind, score]
		self.mode = 'default'		# more than one way to run this code: default, cluster, score (rosetta)
		self.resnames = []		# this is populated in the 'surface_conacts' procedure. list of residue names for sequence
		self.ros_frames = -1		# number of "top score" structures to look at. defined with class call (not internal to class)
		self.OVERWRITE = 'n'		# overwrite old files? defined with class call
		self.score_file = ''		# path to Rosetta score file.
		self.first_frame = 0            # 
		self.last_frame = -1            # NEEDS TO BE FIXED!!
		self.sequence = ''		# Required for some calcs

	def analyze_clusters(self):
		"""
		Structures can be characterized by PCA, and the structures can be clustered using k-means in PC-space.
		This function performs a structural analysis on each k-means cluster.
	
		"""
		self.name_mod = '_ros'
		k = np.loadtxt(sa.outdir+'PCA_kmeans_clusters' + sa.name_mod + '.npy')
	
		# Be careful with this. Not all calcs need to be redone (i.e. Rg, SASA, EED, PCA)
		# However, cmaps and SS both need to be recomputed because they were already averaged
		self.calcs = ['flory']
	
		if self.top == "":
			self.load_top()
	
		old_name_mod = self.name_mod
		for cluster in range(int(max(k))+1):
			self.cmaps = []
			self.SS = []
			dcd = md.load_dcd(self.outdir + 'cluster_' + str(cluster) + old_name_mod + '.dcd', self.top)
			self.name_mod = '_cluster_'+str(cluster)
			print "CLUSTER:",cluster
			self.nres = dcd[0].n_residues
			for struc in dcd:
				self.calculations(struc)
	
			if 'cmaps' in self.calcs:
				sa_core.av_cmaps(self.cmaps,self.nres,self.resnames,self.outdir,self.name_mod,"NULL")
			if 'SS' in self.calcs:
				sa_core.av_SS(self.SS)
			if 'flory' in self.calcs:
				self.fex_hist()
		return None

	def load_scores(self,fil): 
		"""
		Parse Rosetta score file for scores

		"""
		score = [] 
		for line in open(fil): 
			list = line.split() 
			if list[1] == "score": 
				continue 
			score.append(float(list[1])) 
		return np.array(score)

	def load_top(self):
		"""
		if PDB list is provided, self.top might need to be supplied. Load first pdb and exit.

		"""
		if self.trajname.split('.')[-1] == 'txt':
			for PDB in open(PDB_list):
				self.top = PDB.split("\n")[0]
				break
		else:
			print "Wrong format. Shouldn't be using this function here..."

		return None

	def check_input(self):
		"""
		This function determines which calcs need to be run

		"""
		# make sure 'outdir' is formatted properly
		try:
			# sometimes I accidentally put / on the end twice
			if self.outdir[-2] == '/' and self.outdir[-1] == '/':
				self.outdir = self.outdir[:-1]
			# sometimes I over-correct and don't put any
			if self.outdir[-1] != '/':
				self.outdir = self.outdir+'/'
		except:
			if self.outdir == '':
				pass
			else:
				print "something is weird here. outdir =", self.outdir

		# if outdir doesn't exist, make it
		if not os.path.exists(self.outdir):
			os.makedirs(self.outdir)

		# if no calculations are specified, run these
		if self.calcs == []:
			for c in ['Gyr', 'Rg', 'SASA', 'EED', 'Asph', 'cmaps', 'SS', 'PCA']:
				if c not in self.calcs:
					self.calcs.append(c)

		# Rg and Asph come from gyration tensor
		if 'Rg' in self.calcs or 'Asph' in self.calcs:
			for c in ['Gyr']:
				if c not in self.calcs:
					self.calcs.append(c)

		# contact maps only from surface residues
		if 'surface_contacts' in self.calcs:
			for c in ['SASA']:
				if c not in self.calcs:
					self.calcs.append(c)

		# PCA requires the following calculations. Make sure they're there
		elif 'PCA' in self.calcs:
			for c in ['Gyr', 'Rg', 'SASA', 'EED', 'Asph']:
				if c not in self.calcs:
					self.calcs.append(c)

		# polymer models based on EED and Rg distributions
		elif 'chain' in self.calcs:
			for c in ['Gyr', 'Rg', 'EED']:
				if c not in self.calcs:
					self.calcs.append(c)

		# make sure all calculations supplied are valid
		for c in self.calcs:
			if c not in ['Rg', 'SASA', 'EED', 'Asph', 'rama', 'cmaps', 'PCA', 'gcmaps','XRg','SS', 'chain', 'score','flory', 'centroids', 'Gyr', 'surface_contacts', 'rmsd', 'probe']:
				print c, "is not a known calculation. Exiting..."
				exit()

		# if ros_frames isn't specified, use 100 by default
		if self.mode == 'score' and self.ros_frames == -1:
			self.ros_frames = 100

		return None

	def overwrite(self):
		"""
		If you want to overwrite old data

		"""
		self.OVERWRITE = 'y'
		return None

	def load_data(self):
		"""
		Don't compute things twice. Load pre-computed data from previous runs

		"""
		self.calcs = np.array(self.calcs)

		if 'Rg' in self.calcs and os.path.isfile(self.outdir+'Rg'+self.name_mod+file_ext):
			print 'loading data for Rg...', self.outdir+'Rg'+self.name_mod+file_ext
			self.Rg = np.loadtxt(self.outdir+'Rg'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'Rg')]
		if 'EED' in self.calcs and os.path.isfile(self.outdir+'EED'+self.name_mod+file_ext):
			print 'loading data for EED...', self.outdir+'EED'+self.name_mod+file_ext
			self.EED = np.loadtxt(self.outdir+'EED'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'EED')]
		if 'Asph' in self.calcs and os.path.isfile(self.outdir+'Asph'+self.name_mod+file_ext):
			print 'loading data for Asph...', self.outdir+'Asph'+self.name_mod+file_ext
			self.Asph = np.loadtxt(self.outdir+'Asph'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'Asph')]
		if 'SASA' in self.calcs and os.path.isfile(self.outdir+'SASA'+self.name_mod+file_ext):
			print 'loading data for SASA...', self.outdir+'SASA'+self.name_mod+file_ext
			self.SASA = np.loadtxt(self.outdir+'SASA'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'SASA')]
		if 'cmaps' in self.calcs and os.path.isfile(self.outdir+'CMAPS'+self.name_mod+file_ext):
			print 'loading data for CMAPS...', self.outdir+'CMAPS'+self.name_mod+file_ext
			cmaps_raw = np.loadtxt(self.outdir+'CMAPS'+self.name_mod+file_ext)
			nres = np.sqrt(cmaps_raw.shape[1]).astype(int)
			self.cmaps = cmaps_raw.reshape(cmaps_raw.shape[0], nres, nres)
			self.calcs = self.calcs[np.where(self.calcs != 'cmaps')]
		if 'gcmaps' in self.calcs and os.path.isfile(self.outdir+'GCMAPS'+self.name_mod+file_ext):
			print 'loading data for GCMAPS...', self.outdir+'GCMAPS'+self.name_mod+file_ext
			self.gcmaps = np.loadtxt(self.outdir+'GCMAPS'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'gcmaps')]
		if 'rama' in self.calcs and os.path.isfile(self.outdir+"RAMA_all" + self.name_mod + ".npy"):
			print 'loading dihedrals...', self.outdir+"RAMA_all" + self.name_mod + ".npy"
			self.dihedrals = np.loadtxt(self.outdir+"RAMA_all" + self.name_mod + ".npy")
			self.calcs = self.calcs[np.where(self.calcs != 'rama')]
		if 'SS' in self.calcs and os.path.isfile(self.outdir+'SS_H'+self.name_mod+file_ext):
			print 'loading data for SS...', self.outdir+'SS_H'+self.name_mod+file_ext
			nres,nframes = np.loadtxt(self.outdir+'SS_H'+self.name_mod+file_ext).shape
			self.SS = np.zeros((3,nres,nframes))
			self.SS[0] = np.loadtxt(self.outdir+'SS_H'+self.name_mod+file_ext)
			self.SS[1] = np.loadtxt(self.outdir+'SS_E'+self.name_mod+file_ext)
			self.SS[2] = np.loadtxt(self.outdir+'SS_C'+self.name_mod+file_ext)
			self.calcs = self.calcs[np.where(self.calcs != 'SS')]
		if 'PCA' in self.calcs or 'centroids' in self.calcs:
			# This is a special case. If all of the files already exist, don't bother loading them.
			# The calculation is complete.
			pca1 = self.outdir+'PCA_kmeans_clusters' + self.name_mod + '.npy'
			pca2 = self.outdir+'PCA_kmeans_A' + self.name_mod + '.npy'
			pca3 = self.outdir+'PCA_kmeans_B' + self.name_mod + '.npy'
			if (os.path.isfile(pca1) and os.path.isfile(pca1) and os.path.isfile(pca1)) and 'centroids' not in self.calcs:
				print "skipping PCA calculation..."
				self.calcs = self.calcs[np.where(self.calcs != 'PCA')]
			elif (os.path.isfile(pca1) and os.path.isfile(pca1) and os.path.isfile(pca1)) and 'centroids' in self.calcs:
				print "loading PCA data..."
				print pca1
				print pca2
				print pca3
				self.k = np.loadtxt(pca1)
				self.A = np.loadtxt(pca2)
				self.B = np.loadtxt(pca3)
			else:
				pass
		print 'DONE loading data'
		return None

	def write_data(self):
		"""
		This is the core data used by many features of the code. Save it so it doesn't need
		to be recomputed

		"""
		if 'Rg' in self.calcs:
			np.savetxt(self.outdir+'Rg'+self.name_mod+file_ext,self.Rg)
		if 'EED' in self.calcs:
			np.savetxt(self.outdir+'EED'+self.name_mod+file_ext,self.EED)
		if 'Asph' in self.calcs:
			np.savetxt(self.outdir+'Asph'+self.name_mod+file_ext,self.Asph)
		if 'SASA' in self.calcs:
			np.savetxt(self.outdir+'SASA'+self.name_mod+file_ext,self.SASA)
		# cmaps and SS require more processing before they can be saved. They will be saved in the av_cmaps & av_SS functions
		return None

	def calculations(self,struc):
		"""
		Run calculations specified in self.calcs. Before running calculation, check
		to make sure it wasn't already done. If it was done before, load the data.

		"""
		coors = struc.xyz[0] 
		CA_coors = struc.atom_slice(struc.topology.select('name CA'))[0].xyz[0]

		self.nres = struc.n_residues
		if 'Gyr' in self.calcs:
			L = sa_core.gyration_tensor(coors)
		if 'Rg' in self.calcs:
			#self.Rg.append(md.compute_rg(struc)[0])
			self.Rg.append(sa_core.compute_Rg(L))
		if 'Asph' in self.calcs:
			self.Asph.append(sa_core.compute_Asph(L))
		if 'EED' in self.calcs:
			self.EED.append(np.linalg.norm(CA_coors[0]-CA_coors[-1]))
		if 'SASA' in self.calcs:
			SASA = md.shrake_rupley(struc)
			self.SASA.append(SASA.sum(axis=1)[0])
		if 'cmaps' in self.calcs:
			dist = self.contact_maps(CA_coors)
		if 'gcmaps' in self.calcs:
			self.gcmaps.append(sa_core.gremlin_contact_maps(dist))
		if 'SS' in self.calcs:
			self.SS.append(md.compute_dssp(struc))
		if 'flory' in self.calcs:
			self.fex.append(polymer.compute_flory(struc,self.nres))
		if 'rama' in self.calcs:
			self.dihedrals.append(rama.compute_phipsi(struc))
		if 'surface_contacts' in self.calcs:
			self.resnames = [struc.atom_slice(struc.topology.select('name CA')).topology.atom(r).residue.name for r in range(self.nres)]
			self.scmaps.append(sa_core.surface_contacts(struc,SASA))
		return None

	def run(self,mode='default'):
	        """
		Runs and handles all function calls. All data is stored in class object.

	        """
		from timeit import default_timer as timer

		start = timer()

		global file_ext ; file_ext = '_raw.npy'

		self.mode = mode

		#---Check to see which calculations need to be run
		self.check_input()

		print self.trajname

		#---Load existing data
		if self.mode == 'default' and self.OVERWRITE == 'n': 
			self.load_data()
		elif self.OVERWRITE == 'y':
			print "OVERWRITING OLD DATA!"

		print "calculations left to do:", self.calcs

		#---Decide if it's necessary to load trajectories/PDBs
		if len(self.calcs) == 0: LOAD = False
		else: LOAD = True

		if self.mode == 'default':
			if LOAD == True:
				print "Loading Trajectory"
				traj_ext = self.trajname.split('.')[-1]
				if traj_ext in ['dcd', 'xtc']:
					if traj_ext == 'dcd':
						traj = md.load_dcd(self.trajname, self.top)
					elif traj_ext == 'xtc':
						traj = md.load_xtc(self.trajname, top=self.top)
					if self.last_frame != -1:
						traj = traj[self.first_frame:self.last_frame]
					for struc in traj:
						prot = struc.atom_slice(struc.topology.select('protein'))[0]
						self.calculations(prot)
				# Or, if given a list of PDB's
				elif traj_ext == 'txt':
					for PDB in open(self.trajname):
						struc = md.load(PDB.split("\n")[0])
						self.calculations(struc)
					self.top = PDB.split("\n")[0]
				else:
					print "file type", traj_ext, "not recognized"

				#---Write data
				self.write_data()

		#---Code can be run in special mode where it references a Rosetta score file and only computes statistics on top N structures
		elif self.mode == 'score':
			print "ROSETTA SCORE MODE"
			self.name_mod = '_ros'
			#---Search for score file
			if self.score_file == '':
				success = False
				#---first check the most obvious spot
				if os.path.exists(self.outdir+"score.fsc"):
					scores = self.load_scores(self.outdir+"score.fsc") 
					success = True
				#---maybe it's in a subdirectory
				else:
					for Ind in range(len(self.outdir.split('/'))):
						newpath = ''
						for i in self.outdir.split('/')[:-1*Ind]:
							newpath+=i+'/'
						if os.path.exists(newpath+"score.fsc"): 
							scores = self.load_scores(newpath+"score.fsc") 
							success = True
				#---can't find it using simple methods. Throw an error
				if success == False:
					print "looking for",self.outdir+"score.fsc"
					print "score file could not be located. Exiting..."
					exit()
			#---If name is provided, try to load it. Note: name must be provided using class call (i.e. sa.score_file = '/path/to/score.fsc')
			else:
				scores = self.load_scores(self.score_file) 
			#---Save all Rosetta ID's with their associated scores
			frame_sel = []
			ind = np.argsort(scores)[:self.ros_frames]
			for i in ind:
				self.scores.append([i, scores[i]])
				frame_sel.append(i)
			#---Save associated files in a separate directory
			fr = 0
			if not os.path.exists(self.outdir+"top_score/pdbs"):
				os.makedirs(self.outdir+"top_score/pdbs")
			#---Iterate through pdb's with best scores
			for PDB in open(self.trajname):
				if fr in frame_sel:
					struc = md.load(PDB.split("\n")[0])
					struc.save(self.outdir+"top_score/"+PDB.split("\n")[0].split("/")[-1])
					self.calculations(struc)
					print PDB.split("\n")[0]
				fr += 1
			self.top = PDB.split("\n")[0]

		#---Post-Processing
		if 'cmaps' in self.calcs:
			try: sa_core.av_cmaps(self.cmaps,self.nres,self.resnames,self.outdir,self.name_mod,"NULL")
			except: print "CMAPS didnt work"
		if 'gcmaps' in self.calcs:
			try: sa_core.av_cmaps(self.gcmaps,self.nres,self.resnames,self.outdir,self.name_mod,"gremlin")
			except: print "grem CMAPS didnt work"
		if 'surface_contacts' in self.calcs:
			sa_core.av_cmaps(self.scmaps,self.nres,self.resnames,self.outdir,self.name_mod,"surface")
			#try: self.av_cmaps(self.scmaps,"surface")
			#except: print "surface CMAPS didnt work"
		if 'SS' in self.calcs:
			try: sa_core.av_SS(self.SS)
			except: print "SS didnt work" ; exit()
		if 'EED' in self.calcs and 'Asph' in self.calcs:
			try: sa_core.scatterplot(self.EED, self.Asph, 'EED', 'Asph', 'EED_v_Asph',self.outdir,self.name_mod)
			except: print "didnt work 3"
		if 'Rg' in self.calcs and 'SASA' in self.calcs:
			try: sa_core.scatterplot(self.Rg, self.SASA, 'Rg', 'SASA', 'Rg_v_SASA',self.outdir,self.name_mod)
			except: print "didnt work 4"
		if 'PCA' in self.calcs:
			pca.run_PCA(self.EED,self.Rg,self.SASA,self.Asph,self.outdir,self.name_mod,self.mode,self.scores,self.trajname,self.ros_frames,self.calcs)
		if 'flory' in self.calcs:
			polymer.fex_hist(self.fex,self.outdir,self.name_mod)
		if 'chain' in self.calcs:
			#polymer.gaussian_chain(self.EED,self.Rg,self.outdir,self.name_mod)
			polymer.semiflexible_chain(self.EED,self.outdir,self.name_mod)
		if 'centroids' in self.calcs:
			self.cluster_centroids()
		if 'rama' in self.calcs:
			rama.rama(self.dihedrals,self.outdir,self.name_mod)
		if 'probe' in self.calcs:
			skip_frames = 1
			first_frame = 0
			last_frame = 'last'
			nthreads = 1
			cutoff = 5
			probe_radius = 1.0
			self.sequence = ['R','Q','M','N','F','P','E','R','S','M','D','M','S','N','L','Q','M','D','M','Q','G','R','W','M','D','M','Q','G','R','Y','T','N','P','F','N']
			mem.interface_probe(PDB,XTC,skip_frames,first_frame,last_frame,nthreads,cutoff,probe_radius,sequence)

		end = timer()
		print "Total execution time:", end-start

		return None

def USAGE():
	print "USEAGE: python rosetta_analysis.py ARGS"
	print "ARGS: EITHER a list of pdbs in a file with a .txt extension, or"
	print "a .dcd and a .pdb"
	exit()

if __name__ == "__main__":
	import sys
	if len(sys.argv) == 2:
		if sys.argv[1].split('.')[1] == 'txt':
			PDB_list = sys.argv[1]
			sa = SA(PDB_list,'','_test','analysis',['PCA'])
		else:
			USAGE()
	elif len(sys.argv) == 3:
		if sys.argv[1].split('.')[1] in ['dcd', 'xtc'] and sys.argv[2].split('.')[1] in ['pdb', 'gro']:
			traj = sys.argv[1]
			top = sys.argv[2]
			sa = SA(traj,top,'test','test_traj/',['Rg'])
		else:
			USAGE()
	else:
		USAGE()

	sa.overwrite()
	sa.run()
	#sa.ros_score_sort()
	#kmeans_clusters.write_clusters(sa.k,sa.trajname,sa.top,sa.outdir,sa.name_mod)
	#sa.analyze_clusters()
