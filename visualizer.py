"""
Visualization Module
Creates charts for data usage analysis
"""

import io
import matplotlib
matplotlib.use('Agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from typing import Dict, List, Tuple
from monitor import ProcessStats


class DataVisualizer:
    """Creates and manages data visualizations"""
    
    @staticmethod
    def create_category_pie_chart(
        data: Dict[str, int],
        parent_frame=None
    ) -> Tuple[Figure, None]:
        """
        Create pie chart of data usage by category
        Returns: (Figure, Canvas)
        """
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        if data and sum(data.values()) > 0:
            labels = list(data.keys())
            sizes = list(data.values())
            colors = DataVisualizer._get_category_colors(labels)
            
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                   startangle=90, textprops={'fontsize': 9})
            ax.set_title('Data Usage by Category', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        
        fig.tight_layout()
        
        return fig, None
    
    @staticmethod
    def create_top_processes_chart(
        processes: List[ProcessStats],
        parent_frame=None
    ) -> Tuple[Figure, None]:
        """
        Create bar chart of top processes by data usage
        Returns: (Figure, Canvas)
        """
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        if processes:
            names = [p.process_name[:15] for p in processes]  # Truncate names
            sent = [p.bytes_sent / (1024 * 1024) for p in processes]  # Convert to MB
            recv = [p.bytes_recv / (1024 * 1024) for p in processes]
            
            x = range(len(names))
            width = 0.35
            
            bars1 = ax.bar([i - width/2 for i in x], sent, width, label='Sent (MB)',
                          color='#FF6B6B', alpha=0.8)
            bars2 = ax.bar([i + width/2 for i in x], recv, width, label='Received (MB)',
                          color='#4ECDC4', alpha=0.8)
            
            ax.set_xlabel('Process', fontweight='bold')
            ax.set_ylabel('Data (MB)', fontweight='bold')
            ax.set_title('Top Processes by Data Usage', fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(names, rotation=45, ha='right')
            ax.legend()
            
            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{height:.1f}',
                               ha='center', va='bottom', fontsize=8)
        else:
            ax.text(0.5, 0.5, 'No process data available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        
        fig.tight_layout()
        
        return fig, None
    
    @staticmethod
    def create_risk_distribution_chart(
        risk_data: Dict[str, int],
        parent_frame=None
    ) -> Tuple[Figure, None]:
        """
        Create bar chart of risk level distribution
        Returns: (Figure, Canvas)
        """
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        if risk_data and sum(risk_data.values()) > 0:
            categories = list(risk_data.keys())
            counts = list(risk_data.values())
            colors = [DataVisualizer._get_risk_color(cat) for cat in categories]
            
            bars = ax.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black')
            
            ax.set_ylabel('Connection Count', fontweight='bold')
            ax.set_title('Risk Level Distribution', fontweight='bold')
            ax.set_ylim(0, max(counts) * 1.1 if counts else 1)
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No risk data available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        
        fig.tight_layout()
        
        return fig, None

    @staticmethod
    def figure_to_png_bytes(fig: Figure) -> bytes:
        """Render a matplotlib Figure into PNG bytes for Flask responses."""
        buffer = io.BytesIO()
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        canvas.print_png(buffer)
        return buffer.getvalue()
    
    @staticmethod
    def _get_category_colors(categories: List[str]) -> List[str]:
        """Get colors for categories"""
        color_map = {
            'System': '#87CEEB',      # Sky blue
            'Local': '#87CEEB',        # Sky blue
            'Trusted': '#90EE90',      # Light green
            'CDN': '#87CEEB',          # Sky blue
            'Third-Party': '#FFD700',  # Gold
            'Tracker': '#FF6B6B',      # Red
            'Unknown': '#999999',      # Gray
            'Suspicious': '#8B0000',   # Dark red
        }
        return [color_map.get(cat, '#999999') for cat in categories]
    
    @staticmethod
    def _get_risk_color(risk_level: str) -> str:
        """Get color for risk level"""
        color_map = {
            'LOW': '#90EE90',        # Green
            'MEDIUM': '#FFD700',     # Gold
            'HIGH': '#FF6B6B',       # Red
            'CRITICAL': '#8B0000',   # Dark red
        }
        return color_map.get(risk_level, '#999999')
    
    @staticmethod
    def format_bytes(bytes_val: int) -> str:
        """Format bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    @staticmethod
    def format_speed(kb_per_sec: float) -> str:
        """Format speed to human-readable format"""
        if kb_per_sec < 1024:
            return f"{kb_per_sec:.1f} KB/s"
        elif kb_per_sec < 1024 * 1024:
            return f"{kb_per_sec / 1024:.1f} MB/s"
        else:
            return f"{kb_per_sec / (1024 * 1024):.1f} GB/s"
