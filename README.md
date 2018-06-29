# IDP analysis

Dependencies for full functionality:
	NumPy
	MDTraj
	Matplotlib
	SKLearn
	SciPy
	MDAnalysis (this will soon be eliminated)

This code contains many functions that may be useful for characterizing 
intrinsically disordered proteins. Many functions piggyback off of
MDTraj. This code has only been tested with Python 2.7. 

*A major update was just pushed to github and this new version
likely contains many bugs. The example at the bottom of "sa.py" should
work provided you're running Python 2.7, have correctly formatted input
files, and all of the dependencies.*

The code can do many things. The central idea behind the code is that
IDP's aren't well characterized by rigid geometric descriptors such as
secondary structure and tertiary contacts. These two quantities 
are useful ways to define canonically folded structures, but they don't
lend well to structures that have many metastable states and no 
well-defined folded structure. So, instead, we characterize distributions 
of states using less-specific criteria such as radius of gyration,
asphericity, end-to-end distance, solvent accessible surface area, etc.
We can get a lot of leverage out of these quantities if we have 
enough structures to compute decent statistics. 

So, I mainly use this platform to:
	1. Compute Principle Component Analysis to characterize a 
	distribution of structures
	2. Compute quantities from polymer theory such as the Flory
	exponent
	3. Analyze the surface chemistry of the protein using the
	"surface contacts" function

There are several functions that I no longer use and therefore may not work.
I am actively working on re-writing and optimizing the code (6/2018)
