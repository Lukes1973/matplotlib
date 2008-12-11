import os
files = (
    'alignment_demo.py',
    'annotation_demo.py',
    'axes_demo.py',
    'broken_bar.py', 
    'compare_with_matlab.py',
    'color_demo.py',            
    'date_ticker_demo.py',
    'ellipse_demo.py',
    'figure_mosaic.py',
    'fill_between.py',
    'fonts_demo_kw.py',
    'from_pil.py',
    'image_demo.py',
    'image_origin.py',
    'integral_demo.py',    
    'layer_images.py',
    'linear_regression.py',
    'major_minor_demo.py',
    'mathtext_demo.py',
    'poly_regression.py',
    'radian_demo.py',
    'renderer_agg.py',
    'simple_imshow.py',
    'simple_plot_tkagg.py',
    'specgram_demo.py',
    'subplot_demo.py',
    )

for fname in files:
    print 'Running', fname
    os.system('python %s' % fname)
    

print 'converting renderer_agg to ps'
os.system('convert ../figures/renderer_agg.png ../figures/renderer_agg.ps')