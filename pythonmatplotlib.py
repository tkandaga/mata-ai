import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import matplotlib.patches as mpatches

# Fungsi untuk visualisasi interaktif dengan slider
def interactive_tangent_visualizer():
    """Visualisasi interaktif garis singgung dengan slider"""
    
    # Definisi fungsi dan turunannya
    def f(x):
        return 0.5 * x**2 - 2*x + 1
    
    def df(x):
        return x - 2
    
    # Setup figure dan axes
    fig, ax = plt.subplots(figsize=(12, 8))
    plt.subplots_adjust(bottom=0.25)
    
    # Domain
    x = np.linspace(-2, 6, 1000)
    y = f(x)
    
    # Plot fungsi asli
    line_func, = ax.plot(x, y, 'b-', linewidth=3, label=r'$f(x) = \frac{1}{2}x^2 - 2x + 1$')
    
    # Initial point
    x0_init = 2.0
    y0_init = f(x0_init)
    slope_init = df(x0_init)
    
    # Garis singgung initial
    x_tangent = np.linspace(-2, 6, 100)
    y_tangent = slope_init * (x_tangent - x0_init) + y0_init
    line_tangent, = ax.plot(x_tangent, y_tangent, 'r--', linewidth=2, label='Garis Singgung')
    
    # Titik singgung
    point_tangent, = ax.plot([x0_init], [y0_init], 'ro', markersize=10, 
                             markerfacecolor='yellow', markeredgecolor='red', 
                             markeredgewidth=2, label='Titik Singgung')
    
    # Annotation
    annot = ax.annotate(f'({x0_init:.2f}, {y0_init:.2f})\nGradien: {slope_init:.3f}',
                       xy=(x0_init, y0_init), xytext=(30, 30),
                       textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                       arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2'))
    
    # Info box
    b_init = y0_init - slope_init * x0_init
    equation_text = ax.text(0.02, 0.98, f'Persamaan garis singgung:\ny = {slope_init:.3f}x + {b_init:.3f}',
                           transform=ax.transAxes, fontsize=11,
                           verticalalignment='top',
                           bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))
    
    ax.set_xlabel('x', fontsize=12, fontweight='bold')
    ax.set_ylabel('y', fontsize=12, fontweight='bold')
    ax.set_title('Visualisasi Interaktif Garis Singgung', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right')
    ax.set_xlim(-2, 6)
    ax.set_ylim(-5, 8)
    
    # Slider untuk menggeser titik singgung
    ax_slider = plt.axes([0.15, 0.1, 0.7, 0.03])
    slider = Slider(ax_slider, 'Posisi x₀', -1.5, 5.5, valinit=x0_init, valstep=0.1)
    
    # Update function
    def update(val):
        x0 = slider.val
        y0 = f(x0)
        slope = df(x0)
        
        # Update garis singgung
        y_tangent_new = slope * (x_tangent - x0) + y0
        line_tangent.set_ydata(y_tangent_new)
        
        # Update titik
        point_tangent.set_data([x0], [y0])
        
        # Update annotation
        annot.xy = (x0, y0)
        annot.set_text(f'({x0:.2f}, {y0:.2f})\nGradien: {slope:.3f}')
        
        # Update equation text
        b = y0 - slope * x0
        equation_text.set_text(f'Persamaan garis singgung:\ny = {slope:.3f}x + {b:.3f}')
        
        fig.canvas.draw_idle()
    
    slider.on_changed(update)
    
    # Reset button
    ax_button = plt.axes([0.8, 0.02, 0.1, 0.04])
    button = Button(ax_button, 'Reset', color='lightgray', hovercolor='0.975')
    
    def reset(event):
        slider.reset()
    
    button.on_clicked(reset)
    
    plt.show()


# Animasi garis singgung pada berbagai titik
def animate_tangent_line():
    """Visualisasi animasi garis singgung dengan interpretasi geometris"""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Definisi fungsi
    def f(x):
        return 0.5 * x**2 - 2*x + 1
    
    def df(x):
        return x - 2
    
    x = np.linspace(-2, 6, 1000)
    y = f(x)
    
    # Plot 1: Fungsi dengan multiple garis singgung
    ax1.plot(x, y, 'b-', linewidth=3, label=r'$f(x) = \frac{1}{2}x^2 - 2x + 1$')
    ax1.plot(x, df(x), 'g--', linewidth=2, alpha=0.7, label=r"$f'(x) = x - 2$")
    
    # Titik-titik untuk garis singgung
    x_points = np.linspace(-1, 5, 12)
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(x_points)))
    
    for i, x0 in enumerate(x_points):
        y0 = f(x0)
        slope = df(x0)
        
        # Garis singgung
        x_tang = np.array([x0 - 1.5, x0 + 1.5])
        y_tang = slope * (x_tang - x0) + y0
        
        ax1.plot(x_tang, y_tang, '-', color=colors[i], alpha=0.5, linewidth=1.5)
        ax1.plot(x0, y0, 'o', color=colors[i], markersize=6, alpha=0.8)
    
    # Mark titik stasioner (di mana f'(x) = 0)
    x_stat = 2.0
    y_stat = f(x_stat)
    ax1.plot(x_stat, y_stat, 'r*', markersize=20, label='Titik Stasioner (f\'(x)=0)')
    ax1.axhline(y=y_stat, color='red', linestyle=':', alpha=0.3)
    ax1.axvline(x=x_stat, color='red', linestyle=':', alpha=0.3)
    
    ax1.set_xlabel('x', fontsize=13, fontweight='bold')
    ax1.set_ylabel('y', fontsize=13, fontweight='bold')
    ax1.set_title('Garis Singgung pada Berbagai Titik', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1.set_xlim(-2, 6)
    ax1.set_ylim(-5, 8)
    
    # Plot 2: Interpretasi gradien
    x_grad = np.linspace(-2, 6, 100)
    gradients = df(x_grad)
    
    ax2.plot(x_grad, gradients, 'purple', linewidth=3, label='Gradien = f\'(x)')
    ax2.axhline(y=0, color='k', linestyle='-', alpha=0.5, linewidth=2)
    ax2.fill_between(x_grad, 0, gradients, where=(gradients > 0), 
                     alpha=0.3, color='green', label='f naik (f\'>0)')
    ax2.fill_between(x_grad, 0, gradients, where=(gradients < 0), 
                     alpha=0.3, color='red', label='f turun (f\'<0)')
    
    # Mark titik kritis
    ax2.plot(x_stat, 0, 'r*', markersize=20)
    ax2.axvline(x=x_stat, color='red', linestyle=':', alpha=0.5)
    ax2.text(x_stat, 0.5, 'Titik Kritis\n(f\'=0)', ha='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
    
    ax2.set_xlabel('Posisi x', fontsize=13, fontweight='bold')
    ax2.set_ylabel('Gradien Garis Singgung', fontsize=13, fontweight='bold')
    ax2.set_title('Hubungan Posisi dengan Gradien', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    ax2.set_xlim(-2, 6)
    ax2.set_ylim(-4, 4)
    
    # Tambahkan penjelasan
    textstr = '\n'.join([
        'Konsep Penting:',
        '• Gradien = nilai turunan f\'(x)',
        '• f\'(x) > 0 → fungsi naik',
        '• f\'(x) < 0 → fungsi turun', 
        '• f\'(x) = 0 → titik stasioner',
        '  (maks/min lokal)'
    ])
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.9, pad=0.8)
    ax2.text(0.02, 0.98, textstr, transform=ax2.transAxes, fontsize=11,
            verticalalignment='top', bbox=props, family='monospace')
    
    plt.tight_layout()
    plt.show()


# Demo berbagai jenis fungsi
def multiple_functions_demo():
    """Demonstrasi garis singgung pada berbagai tipe fungsi"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 13))
    axes = axes.flatten()
    
    functions = [
        {
            'f': lambda x: x**2,
            'df': lambda x: 2*x,
            'title': r'Parabola: $f(x) = x^2$',
            'derivative': r"$f'(x) = 2x$",
            'domain': (-3, 3),
            'point': 1.5,
            'color': 'blue'
        },
        {
            'f': lambda x: x**3 - 3*x,
            'df': lambda x: 3*x**2 - 3,
            'title': r'Kubik: $f(x) = x^3 - 3x$',
            'derivative': r"$f'(x) = 3x^2 - 3$",
            'domain': (-3, 3),
            'point': 2,
            'color': 'green'
        },
        {
            'f': lambda x: np.sin(x),
            'df': lambda x: np.cos(x),
            'title': r'Sinus: $f(x) = \sin(x)$',
            'derivative': r"$f'(x) = \cos(x)$",
            'domain': (-2*np.pi, 2*np.pi),
            'point': np.pi/4,
            'color': 'purple'
        },
        {
            'f': lambda x: np.exp(x/2),
            'df': lambda x: 0.5*np.exp(x/2),
            'title': r'Eksponensial: $f(x) = e^{x/2}$',
            'derivative': r"$f'(x) = 0.5e^{x/2}$",
            'domain': (-3, 3),
            'point': 1,
            'color': 'orange'
        }
    ]
    
    for i, func_data in enumerate(functions):
        ax = axes[i]
        f = func_data['f']
        df = func_data['df']
        domain = func_data['domain']
        x0 = func_data['point']
        color = func_data['color']
        
        x = np.linspace(domain[0], domain[1], 1000)
        y = f(x)
        
        # Plot fungsi
        ax.plot(x, y, color=color, linewidth=3, label='f(x)')
        
        # Hitung garis singgung
        y0 = f(x0)
        slope = df(x0)
        y_tangent = slope * (x - x0) + y0
        
        # Plot garis singgung
        ax.plot(x, y_tangent, 'r--', linewidth=2.5, label='Garis Singgung', alpha=0.8)
        
        # Plot titik singgung
        ax.plot(x0, y0, 'ro', markersize=12, markerfacecolor='yellow',
               markeredgecolor='red', markeredgewidth=3, zorder=5)
        
        # Annotation dengan arrow
        ax.annotate(f'({x0:.2f}, {y0:.2f})\nm = {slope:.3f}',
                   xy=(x0, y0), xytext=(40, 40),
                   textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.9),
                   arrowprops=dict(arrowstyle='->', lw=2, connectionstyle='arc3,rad=0.3'),
                   fontsize=10, fontweight='bold')
        
        ax.set_title(f'{func_data["title"]}\n{func_data["derivative"]}', 
                    fontsize=12, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=10)
        ax.axhline(y=0, color='k', linewidth=0.8, alpha=0.3)
        ax.axvline(x=0, color='k', linewidth=0.8, alpha=0.3)
        
        # Persamaan garis singgung
        b = y0 - slope * x0
        if b >= 0:
            equation = f'y = {slope:.3f}x + {b:.3f}'
        else:
            equation = f'y = {slope:.3f}x - {abs(b):.3f}'
        
        ax.text(0.02, 0.98, f'Garis singgung:\n{equation}', 
               transform=ax.transAxes, fontsize=10,
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9),
               family='monospace')
    
    plt.tight_layout()
    fig.suptitle('Garis Singgung pada Berbagai Jenis Fungsi', 
                fontsize=16, fontweight='bold', y=1.005)
    plt.show()


# Visualisasi konsep turunan sebagai limit
def derivative_as_limit_demo():
    """Demonstrasi konsep turunan sebagai limit dari garis sekan"""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    def f(x):
        return 0.3 * x**2 - x + 2
    
    def df(x):
        return 0.6 * x - 1
    
    x = np.linspace(-2, 6, 1000)
    y = f(x)
    
    # Plot fungsi
    ax.plot(x, y, 'b-', linewidth=3, label='f(x)')
    
    # Titik tetap
    x0 = 3.0
    y0 = f(x0)
    ax.plot(x0, y0, 'ro', markersize=12, markerfacecolor='red', 
           markeredgecolor='darkred', markeredgewidth=2, zorder=5, label='Titik P')
    
    # Berbagai garis sekan yang mendekat ke garis singgung
    h_values = [2.0, 1.5, 1.0, 0.5, 0.2]
    colors_sekan = plt.cm.autumn(np.linspace(0, 0.8, len(h_values)))
    
    for i, h in enumerate(h_values):
        x1 = x0 + h
        y1 = f(x1)
        
        # Garis sekan
        slope_sekan = (y1 - y0) / h
        x_sekan = np.array([x0 - 1, x0 + h + 1])
        y_sekan = slope_sekan * (x_sekan - x0) + y0
        
        ax.plot(x_sekan, y_sekan, '--', color=colors_sekan[i], linewidth=1.5,
               alpha=0.7, label=f'Sekan (h={h})')
        ax.plot(x1, y1, 'o', color=colors_sekan[i], markersize=8, alpha=0.8)
    
    # Garis singgung (limit h→0)
    slope_tangent = df(x0)
    x_tang = np.linspace(-2, 6, 100)
    y_tang = slope_tangent * (x_tang - x0) + y0
    ax.plot(x_tang, y_tang, 'g-', linewidth=3, label='Garis Singgung (h→0)', zorder=4)
    
    ax.set_xlabel('x', fontsize=13, fontweight='bold')
    ax.set_ylabel('y', fontsize=13, fontweight='bold')
    ax.set_title('Turunan sebagai Limit dari Garis Sekan', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper left', fontsize=9)
    ax.set_xlim(-1, 6)
    ax.set_ylim(-1, 6)
    
    # Penjelasan matematis
    textstr = '\n'.join([
        'Konsep Limit:',
        '',
        "f'(x₀) = lim[h→0] (f(x₀+h) - f(x₀))/h",
        '',
        'Saat h mengecil:',
        '• Garis sekan → Garis singgung',
        '• Gradien sekan → Gradien singgung',
        "• Rasio perubahan → f'(x₀)"
    ])
    
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.95, pad=1)
    ax.text(0.62, 0.05, textstr, transform=ax.transAxes, fontsize=11,
            verticalalignment='bottom', bbox=props, family='monospace')
    
    plt.tight_layout()
    plt.show()


# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("VISUALISASI GARIS SINGGUNG DAN TURUNAN")
    print("=" * 60)
    print("\nMenu:")
    print("1. Visualisasi Interaktif (dengan slider)")
    print("2. Animasi Garis Singgung Multi-Titik")
    print("3. Demo Berbagai Fungsi")
    print("4. Konsep Turunan sebagai Limit")
    print("5. Jalankan Semua Visualisasi")
    print("=" * 60)
    
    choice = input("\nPilih menu (1-5) atau Enter untuk semua: ").strip()
    
    if choice == '1':
        print("\n▶ Menampilkan visualisasi interaktif...")
        print("  Geser slider untuk mengubah posisi titik singgung!")
        interactive_tangent_visualizer()
        
    elif choice == '2':
        print("\n▶ Menampilkan animasi garis singgung...")
        animate_tangent_line()
        
    elif choice == '3':
        print("\n▶ Menampilkan demo berbagai fungsi...")
        multiple_functions_demo()
        
    elif choice == '4':
        print("\n▶ Menampilkan konsep turunan sebagai limit...")
        derivative_as_limit_demo()
        
    else:
        print("\n▶ Menjalankan semua visualisasi...")
        print("\n[1/4] Visualisasi Interaktif")
        interactive_tangent_visualizer()
        
        print("\n[2/4] Animasi Garis Singgung")
        animate_tangent_line()
        
        print("\n[3/4] Demo Berbagai Fungsi")
        multiple_functions_demo()
        
        print("\n[4/4] Konsep Turunan sebagai Limit")
        derivative_as_limit_demo()
    
    print("\n" + "=" * 60)
    print("✅ Visualisasi selesai!")
    print("=" * 60)