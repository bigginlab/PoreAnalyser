import streamlit as st
import sys
sys.path.append('PoreAnalyser/')
#import hole_analysis as hole_analysis
import os
import io
import MDAnalysis
from stmol import showmol
import py3Dmol
import numpy as np
from visualization import plt_ellipsoid_pathway, st_write_ellipsoid, example_xy_plane, compare_volume, write_pdb_with_ellipsoid_surface, st_write_conductance_estimation
# pathway_visu, write_pdb_with_pore_surface,
from download_files import download_output, download_Ellipsoid_output

import PoreAnalyser as pf

try:
    import multiprocessing 
    print("Number of processors: ", multiprocessing.cpu_count())
    #st.write("Number of processors: ", multiprocessing.cpu_count())
    parallel = True
except:
    parallel = False
    st.write("Could not import multiprocessing library, => multiprocessing disabled")
sys.path.append('PoreAnalyser/ProbeParticleEllipsoid/')
from ellipsoid_optimisation import ellipsoid_pathway
import pandas as pd
import matplotlib.pyplot as plt

st.title("PoreAnalyser: Exploring the Influence of Pore Shape on Conductance and Permeation")
#st.title("Extending the capabilities of the HOLE Package for Annotation of Ion Channels")

str1 = 'Over the last two decades, advances in structural biology along with recent artificial intelligence–driven structure prediction '
str2 = 'algorithms, such as AlphaFold, have revealed a plethora of 3-D ion channel and nanopore structures in different conformational states. '
str3 = 'However, in nearly every case, these structures still require functional annotation. '
str4 = 'Different tools, such as HOLE and CHAP, allow the analysis of the physical dimensions of the pore running through an ion channel. '
str5 = 'Here, we present an interactive web-service based on the PoreAnalyser python package that allows users to calculate the pore profile of any input structure. '
str6 = 'Based on the well-established HOLE programme, we add a new feature to capture pore asymmetry by using an ellipsoidal probe particle. '
st.write(str1+str2+str3+str4+str5+str6)
url1 = "https://porefinding.readthedocs.io/en/latest/index.html"
url2 = "https://porefinding.readthedocs.io/en/latest/visualisation.html"
str1 = "The [documentation](%s) of the PoreAnalyser python package " % url1
str2 = "gives more information about [visualisation](%s) with the output files that you can download here." % url2
st.write(str1+str2)
url1 = "https://doi.org/10.1016/j.bpj.2024.07.010"
str1 = "The [publication](%s) corresponding to the PoreAnalyser python package " % url1
str2 = " ivestigates the influence of pore shape on conductance and permeation."
str3 = " Please cite [Seiferth and Biggin, 2024](%s) when you use PoreAnalyser." % url1
st.write(str1+str2+str3)

st.subheader("Pathway Finding Settings")
string1 = 'Radius in Å, which is considered to be the end of the pore. '
string2 = 'This keyword can be used to specify the radius above '
string3 = 'which the program regards a result as indicating that the end of the pore has been reached. '
string4 = 'This may need to be increased for large channels, or reduced for small channels. '
end_radius = st.text_input(label=r'end_radius in $\AA$', value='15', max_chars=3,
              help=string1+string2+string3+string4)
end_radius = int(end_radius)
st.write('The current end_radius is', end_radius, r'$\AA$')

string1 = 'Set to False if the protein is already aligned (pore should be parallel to z-axis)'
align_bool = st.text_input(label='Align the largest prinicpal component to z-axis before pathway calculations (default: True)', value='True', max_chars=5,
              help=string1)
if align_bool == 'True':
    align_bool = True
    st.write('The largest principal component of the uploaded protein will be aligned to the z-axis.')
else:
    align_bool = False
    st.write('The uploaded protein will not be aligned.')
string1 = "If uploaded file is no protein use for instance 'resname UNK'"
pathway_sel = st.text_input(label='Selection to perform HOLE analysis on (default: protein)', value='protein', 
              help=string1)

string1 = 'Set to True if you want to run the pore finding algorithm with an ellipsoidal probe particle (runtime ~1min).'
plt_ellipsoid = st.text_input(label='Run additional pore finding algorithm with ellipsoidal probe particle (default: True)', value='True', 
              help=string1)
if plt_ellipsoid == 'True':
    plt_ellipsoid = True
else:
    plt_ellipsoid = False

st.subheader("Plotting options")
fig_format = st.text_input(label='Format to download pathway figure', value='png', max_chars=4,
              help='default: png, other options: jpeg, tiff, eps, pdf, ...')
string1 = r'The dashed red line indicates where the pore radius is to tight for a water molecule (r < 1.15 $\AA$). '
string2 = r'The dashed green line indicates where there is room for a single water (r < 2.30 $\AA$).'
st.write(string1+string2)
plot_lines = st.text_input(label='Plot red and green lines (default: True)', value='True', max_chars=5,
              help=string1+string2)
if plot_lines == 'True':
    plot_lines = True
else:
    plot_lines = False
title = st.text_input(label='Write a title for your plot', value='', help='Title string for plot')
f_size = st.text_input(label='Font size for figure', value='22', help='default=22')
f_size = int(f_size)

st.subheader("Pathfinding with a spherical probe particle (HOLE)")
string1 = "HOLE is a program that allows the analysis and visualisation of the pore dimensions of the holes "
string2 = "through molecular structures of ion channels (Smart et al., 1996)."
st.write(string1+string2)
string1 = "Here, we use the MDAnalysis interface for HOLE to analyse an ion channel pore or transporter pathway. "
string2 = "The original HOLE documentation can be found here: https://www.holeprogram.org"
st.write(string1+string2)

st.subheader("Pathfinding with an ellipsoidal probe particle")

string1 = "Choose a optimization method for growing the ellipsoidal probe particle, maximising the pore radius. "
opt_method = st.text_input(label='Minimization method (default: nelder-mead, alternatives: Powell, ...)', value='nelder-mead', 
              help=string1)
st.write('You have chosen: ', opt_method)

str0 = 'General procedure to grow an ellipsoidal probe particle based on a spherical probe particle:\n'
str1 = 'Loop through all spherical probe particles:\n'
str2 = 'a) Ellipsoid initialized with spherical probe particle parameters from HOLE output.\n'
str3 = 'b) First Nelder-Mead 4-dim optimization to insert ellipsoid with smaller bounds for parameters [x, y, r1, θ ].\n'
str4 = 'c) Second optimization with larger boundaries for parameters to further increase ellipsoid. The loop takes around 60s to complete...'
st.write(str0+str1+str2+str3+str4)

st.subheader("Parameter for conductance estimation")
str0 = "In the development of a physical model to predict conductance through ion channels, Hille initially considered a cylindrical approximation with length L" 
str1 = " and cross-sectional area A, allowing the resistance R to be expressed as  "
st.write(str0+str1)
st.latex(r''' R = \dfrac{1}{g} = \dfrac{\rho L}{A} ''')
str0 = r'where $\rho$ represents bulk resistivity. This simplistic model was subsequently refined with a more accurate representation of ion channels'
str1 = ' as a series of stacked cylinders, where the resistance accumulates. Considering ohmic principles and utilizing the HOLE software, '
str2 = 'which measures cross-sectional areas A(z) along the channel axis z, the refined resistance model becomes'
st.write(str0+str1)
st.latex(r''' R_{HOLE} = \dfrac{1}{g_{HOLE}} = \sum_i \dfrac{\rho_{bulk} (z_i-z_{i-1})}{\pi r_i^2} ''')
str0 = r'However, relying on bulk property resistivity becomes problematic, as conductivity $\kappa=1/\rho$ depends on the diffusion coefficients of ions. '
str1 = r'The bulk conductivity $\kappa_{bulk}$ of a KCl solution with concentration c is defined as  '
st.write(str0+str1)
st.latex(r''' \kappa_{bulk} = \dfrac{c\cdot q_e^2\cdot(D_K+D_{CL})}{k_B T}''')
str0 = r'where $c$ is the concentration of salts in water, $q_e$ is the elementary charge, $D_K$ and $D_{CL}$ are diffusion coefficients of potassium and chloride ions,' 
str1 = r'$k_B$ is the Boltzmann constant, and $T$ is temperature. '
str2 = r'To refine the model for ion channel conductance further, we introduce a conductivity model, expressing the conductivity  $\kappa(a,b)$ as a function '
str3 = r'of the radii $a$ and $b$ of ellipsoidal probe particles. For larger radii, the ion movement is relatively unconstrained, resulting in  $\kappa(a,b)\approx \kappa_{bulk}$, '
str3 = r'while narrower constrictions with smaller radii lead to reduced conductivity $\kappa(a,b)<\kappa_{bulk}. '
str4 = r'Hence, we can further adapt the model for channel resistance / conductance based on the PoreAnalyser profile to'
st.write(str0+str1+str2+str3+str4)
st.latex(r''' R_{PA} = \dfrac{1}{g_{PA}} = \sum_i \dfrac{(z_i-z_{i-1})}{\kappa(a_i,b_i)\cdot\pi\cdot a_i\cdot b_i} ''')

D_cation = st.text_input(label='Diffusion coefficient of the cation [m^2/s].', value=1.8e-9, help='Default is 1.8e-9 m^2/s (value for potassium)')
D_cation = float(D_cation)
D_anion = st.text_input(label='Diffusion coefficient of the anion [m^2/s].', value=2.032e-9, help='Default is 2.032e-9 m^2/s (value for chloride)')
D_anion = float(D_anion)
popt0 = st.text_input(label=r'Scaling parameters for the conductivity model [1/$\AA$].', value=1.40674664, help='Default is 1.40674664')
popt1 = st.text_input(label=r'Shifting parameters for the conductivity model [dimensionless].', value=1.25040698, help='Default is 1.25040698')
popt = [float(popt0), float(popt1)]
temp = st.text_input(label='Temperature in Kelvin.', value=300, help='Default is 300 K')
temp = float(temp)
c_m = st.text_input(label='Concentration in mol/l.', value=0.15, help='Default is 0.15 mol/l')
c_m = float(c_m)

st.subheader("Upload pdb file(s)")
uploaded_files = st.file_uploader("Choose a file", label_visibility="visible",  accept_multiple_files=True )

labels = []
names = []
names_aligned = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        #st.write("Filename: ", uploaded_file.name)
        labels.append(uploaded_file.name[:-4])
        names.append(uploaded_file.name)
        names_aligned.append(uploaded_file.name[:-4]+'_aligned_z.pdb')
        with open(uploaded_file.name,"wb") as f:
            f.write(uploaded_file.getbuffer())
    #st.write('Uploaded: names_aligned', names_aligned)
    c = pf.PoreAnalysis(names, num_circle=20, align_bool=align_bool, end_radius=end_radius, pathway_sel = pathway_sel,
                        D_cation=D_cation, D_anion=D_anion, popt=popt, temp=temp, c_m=c_m)
    fig, df =  c.hole_analysis(plot_lines=True, legend_outside=False, title='', f_size=15, ) 

    if align_bool: st.write('First, we align the principal axis to the z-axis.')
    #fig , df = hole_analysis.analysis(names, labels=labels, path='', end_radius=end_radius, title=title,
    #                                        legend_outside=False, plot_lines=plot_lines, f_size=f_size, align_bool=align_bool, 
    #                                        sel=pathway_sel                                        )
    st.pyplot(fig)
    path_save = ''
    st.write("Pathway visualisation for ", names[0])
    #write_pdb_with_pore_surface(path=path_save, name=names[0], end_radius=end_radius, num_circle = 24)
    #xyzview = pathway_visu(path=path_save, name=names[0], pathway_sel=pathway_sel)
    xyzview = c.pathway_visualisation(index_model=0, f_end='_circle.pdb')
    showmol(xyzview, height=500, width=710)

    st.subheader("Download HOLE output files")
    df.to_csv('hole_pathway_profile.csv',sep=',')
    fn ="hole_pathway_profile."+fig_format
    fig.savefig(fn, format=fig_format, bbox_inches='tight')
    ### Download ###
    download_output(names_aligned[0][:-4], fn, df, fig, fig_format, path_save, names )

    ### Elipsoid ###
    if plt_ellipsoid:
        st_write_ellipsoid()
        df_res = c.ellipsoid_analysis(index_model=0)
        fig = c.plt_pathway_ellipsoid(index_model=0)
        #ellipsoid_pathway(p=path_save, 
        #                    pdb_name = names_aligned[0], 
        #                    sph_name = names_aligned[0][:-4], 
        #                    slice_dz=4, parallel=parallel, #True, 
        #                    num_processes=None, timeout=6, 
        #                    start_index = 1, end_radius=end_radius-1,
        #                    out = 0,
        #                    n_xy_fac = 3,#1.6,
        #                    pathway_sel=pathway_sel,
        #                    opt_method=opt_method,                )
        print(path_save + names_aligned[0]+ '_pathway_ellipse.txt')
        #res = np.loadtxt(path_save + names_aligned[0]+ '_pathway_ellipse.txt', comments='#', delimiter=',')
        #print('res.shape',res.shape)
        #df_res = pd.DataFrame(data=res, columns=['x', 'y', 'z', 'a', 'b', 'theta'])
        #df_res.sort_values('z', inplace=True)
        #fig = plt_ellipsoid_pathway(df_res, f_size=f_size, title=title, end_radius=end_radius)
        st.pyplot(fig)
        ### visualization for ellipsoidal surface ###
        #write_pdb_with_ellipsoid_surface(p='', pdbname=names_aligned[0], 
        #                                fname=names_aligned[0]+'_pathway_ellipse.txt', num_circle = 24)
        #xyzview = pathway_visu(path='', name=names_aligned[0], f_end='_ellipsoid.pdb', pathway_sel=pathway_sel,)
        xyzview = c.pathway_visualisation(0, f_end='_ellipsoid.pdb')
        showmol(xyzview, height=500, width=710)

        ### compare volumes ###
        res = np.loadtxt(names_aligned[0][:-4] + '.pdb_pathway_ellipse.txt', 
                    comments='#', delimiter=',')
        compare_volume(res, digit=1)

        ### compare mean and standard deviation of two radii ###
        a = df_res['a']
        b = df_res['b']
        st.write('Median',np.mean(a),'Mean and standard dev. of larger radius:',np.mean(a), np.std(a), 'min', min(a), 'max' , max(a) )
        st.write('Median',np.mean(b),'Mean and standard dev.of smaller radius:', np.mean(b), np.std(b), 'min', min(b), 'max' , max(b) ) 

        ### conductnace estimates ###
        hole1, pf1, hole_c, pf1_c, fig = c.conductance_estimation(index_model=0)
        st_write_conductance_estimation(hole1, pf1, hole_c, pf1_c, fig)

        ### Download Ellipsoid output###
        st.subheader("Download files for pathway with ellipsoidal probe particle")
        fn ="ellipsoid_pathway_profile."+fig_format
        fig.savefig(fn, format=fig_format, bbox_inches='tight')
        download_Ellipsoid_output(names_aligned[0][:-4], fn, path_save)
    else:
        st.write('Ellipsoid pathway calculation not activated. To activate set plt_ellipsoid = True')

    #st.write('ERROR with', names)
else:
    st.markdown("Example application with 7tu9")
    st.write("Example Filename: ", "pdb_models/7tu9.pdb")
    if align_bool: st.write('First, we align the principal axis to the z-axis.')
    path_save = 'PoreAnalyser/pdb_models/'
    titles = [r'$\alpha$$\beta$ Heteromeric Glycine Receptor']

    labels = [
        '', #'GlyR-Stry', 
        #'GlyR-Gly',
        #'GlyR-Gly-Ivm'
            ]
    names = [
        '7tu9.pdb', #'GlyR-Stry', 
        #'7tvi.pdb', #'GlyR-Gly',
        #'8fe1.pdb', # 'GlyR-Gly-Ivm'
    ]
    c = pf.PoreAnalysis(names, num_circle=20, path_save=path_save, align_bool=align_bool, end_radius=end_radius, pathway_sel = pathway_sel,
                        D_cation=D_cation, D_anion=D_anion, popt=popt, temp=temp, c_m=c_m)
    fig, csv =  c.hole_analysis(plot_lines=True, legend_outside=False, title='', f_size=15, ) 

    #fig ,csv = hole_analysis.analysis(names, labels=labels, path=path_save, 
    #                         end_radius=end_radius, 
    #                   #TMD_lower=59, TMD_higher=97,
    #                   title=titles[0], 
    #                   legend_outside=False,
    #                   plot_lines=plot_lines,
    #                   f_size=f_size)

    st.pyplot(fig)
    #write_pdb_with_pore_surface(path=path_save, name=names[0], end_radius=end_radius, num_circle = 24)
    # https://github.com/napoles-uach/stmol
    # https://william-dawson.github.io/using-py3dmol.html
    #xyzview = pathway_visu(path=path_save, name=names[0])
    xyzview = c.pathway_visualisation(index_model=0, f_end='_circle.pdb')
    showmol(xyzview, height=500, width=710)
    #render_visu(path='PoreAnalyser/pdb_models/', name='7tu9_aligned_z.pdb')

    ### Ellipsoidal probe particle ###
    st_write_ellipsoid()
    fig_example = example_xy_plane(f_size=f_size)
    st.pyplot(fig_example)

    res = np.loadtxt('PoreAnalyser/pdb_models/7tu9_aligned_z.pdb_pathway_ellipse.txt', 
                 comments='#', delimiter=',')
    df_res = pd.DataFrame(data=res, columns=['x', 'y', 'z', 'a', 'b', 'theta'])
    df_res.sort_values('z', inplace=True)
    fig = plt_ellipsoid_pathway(df_res, f_size=f_size, title=title, end_radius=end_radius)
    st.pyplot(fig)
    #write_pdb_with_ellipsoid_surface(p='PoreAnalyser/pdb_models/', pdbname='7tu9_aligned_z.pdb',
    #                                 fname='7tu9_aligned_z.pdb_pathway_ellipse.txt', num_circle = 24)
    #xyzview = pathway_visu(path='PoreAnalyser/pdb_models/', name='7tu9_aligned_z.pdb', f_end='_ellipsoid.pdb')
    xyzview = c.pathway_visualisation(index_model=0, f_end='_ellipsoid.pdb')
    
    # render_visu(path='PoreAnalyser/pdb_models/', name='7tu9_aligned_z.pdb', f_end='_ellipsoid.pdb', outname='_ellipsoid')

    ### compare volumes ###
    res = np.loadtxt('PoreAnalyser/pdb_models/7tu9_aligned_z.pdb_pathway_ellipse.txt', 
                 comments='#', delimiter=',')
    compare_volume(res, digit=1) 

    ### conductnace estimates ###
    hole1, pf1, hole_c, pf1_c, fig = c.conductance_estimation()
    st_write_conductance_estimation(hole1, pf1, hole_c, pf1_c, fig)


#st.write(os.listdir())
st.subheader("References")
st.write("Smart, O.S., Neduvelil, J.G., Wang, X., Wallace, B.A., Sansom, M.S.P., 1996. HOLE: A program for the analysis of the pore dimensions of ion channel structural models. Journal of Molecular Graphics 14, 354–360. https://doi.org/10.1016/S0263-7855(97)00009-X")
st.write("Gowers, R., Linke, M., Barnoud, J., Reddy, T., Melo, M., Seyler, S., Domański, J., Dotson, D., Buchoux, S., Kenney, I., Beckstein, O., 2016. MDAnalysis: A Python Package for the Rapid Analysis of Molecular Dynamics Simulations. Presented at the Python in Science Conference, Austin, Texas, pp. 98–105. https://doi.org/10.25080/Majora-629e541a-00e")
st.write("Seiferth, D., Biggin, P. C., 2024. Exploring the Influence of Pore Shape on Conductance and Permeation. Biophysical Journal. https://doi.org/10.1016/j.bpj.2024.07.010")
