"""
PDF Service - Generate PDF documents
"""

from datetime import datetime
from flask import current_app
import io

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class PDFService:
    """Service for generating PDF documents"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
    
    def generate_pharmacy_bill_pdf(self, bill):
        """
        Generate PDF for pharmacy bill
        
        Args:
            bill: PharmacyBill object
            
        Returns:
            bytes: PDF content
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        # Hospital Header
        hospital_name = current_app.config.get('HOSPITAL_NAME', 'Smart Hospital')
        elements.append(Paragraph(hospital_name, title_style))
        elements.append(Paragraph("Pharmacy Bill", styles['Heading2']))
        elements.append(Spacer(1, 20))
        
        # Bill Info
        bill_info = [
            ['Bill Number:', bill.bill_number],
            ['Date:', bill.created_at.strftime('%Y-%m-%d %H:%M')],
            ['Patient:', bill.patient.full_name if bill.patient else 'N/A'],
            ['Patient ID:', bill.patient.patient_id if bill.patient else 'N/A'],
        ]
        
        if bill.prescription:
            bill_info.append(['Prescription:', bill.prescription.prescription_id])
        
        info_table = Table(bill_info, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # Items Table
        items_data = [['#', 'Medicine', 'Batch', 'Qty', 'Unit Price', 'Total']]
        
        for i, item in enumerate(bill.items, 1):
            items_data.append([
                str(i),
                item.medicine_name,
                item.batch_number or '-',
                str(item.quantity),
                f"₹{item.unit_price:.2f}",
                f"₹{item.total_price:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[30, 180, 70, 40, 70, 70])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        # Totals
        totals_data = [
            ['Subtotal:', f"₹{bill.subtotal:.2f}"],
            ['Tax:', f"₹{bill.tax:.2f}"],
        ]
        
        if bill.discount > 0:
            totals_data.append(['Discount:', f"-₹{bill.discount:.2f}"])
        
        if bill.insurance_covered > 0:
            totals_data.append(['Insurance Coverage:', f"-₹{bill.insurance_covered:.2f}"])
        
        totals_data.append(['Total:', f"₹{bill.total_amount:.2f}"])
        totals_data.append(['Amount Paid:', f"₹{bill.amount_paid:.2f}"])
        
        balance = bill.total_amount - bill.amount_paid - bill.insurance_covered
        if balance > 0:
            totals_data.append(['Balance Due:', f"₹{balance:.2f}"])
        
        totals_table = Table(totals_data, colWidths=[350, 100])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))
        
        # Footer
        elements.append(Paragraph(
            f"Billed by: {bill.pharmacist.full_name if bill.pharmacist else 'N/A'}",
            styles['Normal']
        ))
        elements.append(Paragraph(
            "Thank you for choosing our services!",
            ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_prescription_pdf(self, prescription):
        """
        Generate PDF for prescription
        
        Args:
            prescription: Prescription object
            
        Returns:
            bytes: PDF content
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Hospital Header
        hospital_name = current_app.config.get('HOSPITAL_NAME', 'Smart Hospital')
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        elements.append(Paragraph(hospital_name, title_style))
        elements.append(Paragraph("Prescription", styles['Heading2']))
        elements.append(Spacer(1, 20))
        
        # Prescription Info
        info_data = [
            ['Prescription ID:', prescription.prescription_id, 'Date:', prescription.created_at.strftime('%Y-%m-%d')],
            ['Patient:', prescription.patient.full_name if prescription.patient else 'N/A', 
             'Patient ID:', prescription.patient.patient_id if prescription.patient else 'N/A'],
            ['Doctor:', prescription.doctor.full_name if prescription.doctor else 'N/A',
             'Specialization:', prescription.doctor.specialization if prescription.doctor else 'N/A'],
        ]
        
        info_table = Table(info_data, colWidths=[80, 170, 80, 130])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 15))
        
        # Diagnosis
        elements.append(Paragraph("<b>Diagnosis:</b>", styles['Normal']))
        elements.append(Paragraph(prescription.diagnosis or 'N/A', styles['Normal']))
        elements.append(Spacer(1, 15))
        
        # Medicines
        elements.append(Paragraph("<b>Prescribed Medicines:</b>", styles['Heading3']))
        elements.append(Spacer(1, 10))
        
        med_data = [['#', 'Medicine', 'Dosage', 'Frequency', 'Duration', 'Instructions']]
        
        for i, med in enumerate(prescription.medicines.all(), 1):
            med_data.append([
                str(i),
                med.medicine_name,
                med.dosage,
                med.frequency,
                med.duration,
                med.instructions or '-'
            ])
        
        med_table = Table(med_data, colWidths=[25, 120, 60, 80, 60, 115])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90d9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(med_table)
        elements.append(Spacer(1, 20))
        
        # Notes
        if prescription.notes:
            elements.append(Paragraph("<b>Additional Notes:</b>", styles['Normal']))
            elements.append(Paragraph(prescription.notes, styles['Normal']))
            elements.append(Spacer(1, 15))
        
        # Signature
        elements.append(Spacer(1, 30))
        
        sig_data = [['', '']]
        if prescription.is_signed and prescription.signature_image:
            sig_data = [['', f"Digitally signed on {prescription.signed_at.strftime('%Y-%m-%d %H:%M')}"]]
        
        sig_data.append(['', '_' * 30])
        sig_data.append(['', prescription.doctor.full_name if prescription.doctor else 'Doctor'])
        sig_data.append(['', prescription.doctor.license_number if prescription.doctor else ''])
        
        sig_table = Table(sig_data, colWidths=[300, 160])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTSIZE', (1, 0), (1, 0), 8),
            ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        ]))
        elements.append(sig_table)
        
        # Build PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer.getvalue()