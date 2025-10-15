#!/usr/bin/env python3
"""
Shared styling components for Cloud202 RAPID Assessment Reports
Provides consistent styling across Executive, Technical, and Compliance reports
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for page numbers and headers/footers"""
    def __init__(self, *args, **kwargs):
        # Extract report_type if provided
        self.report_type = kwargs.pop('report_type', 'RAPID Assessment')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        # Page number at bottom center
        self.drawCentredString(
            A4[0] / 2.0,
            0.5 * 0.75 * 72,  # 0.5 inch in points
            f"Page {self._pageNumber} of {page_count}"
        )
        # Company footer
        self.setFont("Helvetica", 8)
        self.drawString(
            0.75 * 72,  # 0.75 inch in points
            0.5 * 72,   # 0.5 inch in points
            f"Cloud202 - {self.report_type}"
        )
        # Footer line
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(0.75 * 72, 0.65 * 72, A4[0] - 0.75 * 72, 0.65 * 72)


def create_enhanced_styles():
    """Create enhanced custom styles for Cloud202 reports"""
    styles = getSampleStyleSheet()
    
    # Only add styles if they don't already exist
    style_names = [s.name for s in styles.byName.values()]
    
    if 'TitlePage' not in style_names:
        styles.add(ParagraphStyle(
            name='TitlePage',
            parent=styles['Title'],
            fontSize=32,
            leading=38,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
    
    if 'Subtitle' not in style_names:
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
    
    if 'MainHeading' not in style_names:
        styles.add(ParagraphStyle(
            name='MainHeading',
            parent=styles['Heading1'],
            fontSize=22,
            leading=28,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=18,
            spaceBefore=28,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#e6f0ff'),
            leftIndent=12,
            rightIndent=12,
            borderPadding=8
        ))
    
    if 'SectionHeading' not in style_names:
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading2'],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=14,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            leftIndent=8
        ))
    
    if 'SubsectionHeading' not in style_names:
        styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=styles['Heading3'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=10,
            spaceBefore=14,
            fontName='Helvetica-Bold',
            leftIndent=12
        ))
    
    if 'BodyText' not in style_names:
        styles.add(ParagraphStyle(
            name='BodyText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2d3748'),
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
    
    if 'BulletPoint' not in style_names:
        styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#2d3748'),
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=6,
            fontName='Helvetica',
            bulletFontName='Helvetica'
        ))
    
    if 'HighlightBox' not in style_names:
        styles.add(ParagraphStyle(
            name='HighlightBox',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#1a365d'),
            backColor=colors.HexColor('#fef5e7'),
            borderWidth=1,
            borderColor=colors.HexColor('#f39c12'),
            borderPadding=10,
            borderRadius=3,
            spaceAfter=12,
            spaceBefore=12
        ))
    
    return styles

