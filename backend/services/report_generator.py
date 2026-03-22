import os
import json
import asyncio
from typing import Dict
from sqlalchemy.orm import Session
from datetime import datetime

from core.database import SessionLocal
from core.config import settings
from models.domain import DocumentMetadata, DocumentReport
from services.email_service import send_report_ready_email
import httpx
import io
import json
import urllib.parse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

# In-Memory Pub/Sub for SSE Streaming Contexts
class ReportStreamManager:
    def __init__(self):
        self.queues: Dict[int, asyncio.Queue] = {}

    def get_queue(self, doc_id: int) -> asyncio.Queue:
        if doc_id not in self.queues:
            self.queues[doc_id] = asyncio.Queue()
        return self.queues[doc_id]

    async def broadcast(self, doc_id: int, event_type: str, data: dict):
        if doc_id in self.queues:
            await self.queues[doc_id].put({"event": event_type, "data": json.dumps(data)})

    def close(self, doc_id: int):
        if doc_id in self.queues:
            del self.queues[doc_id]

stream_manager = ReportStreamManager()

async def generate_pdf_report(report_data: dict, filename: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=24, spaceAfter=20)
    h2_style = ParagraphStyle('Heading2Style', parent=styles['Heading2'], fontSize=16, spaceAfter=12, spaceBefore=18)
    h3_style = ParagraphStyle('Heading3Style', parent=styles['Heading3'], fontSize=13, spaceAfter=10, textTransform='uppercase', textColor='#1e293b')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=11, leading=16, spaceAfter=10)
    
    story = []
    
    story.append(Paragraph(f"Advanced AI Report: {filename}", title_style))
    story.append(Spacer(1, 12))
    
    if "executive_summary" in report_data:
        story.append(Paragraph("Executive Summary", h2_style))
        story.append(Paragraph(report_data["executive_summary"], body_style))
        
    if "data_overview" in report_data:
        story.append(Paragraph("Document Profile", h2_style))
        story.append(Paragraph(report_data["data_overview"], body_style))
        
    if "analysis_text" in report_data:
        story.append(Paragraph("Deep Analysis & Trends", h2_style))
        story.append(Paragraph(report_data["analysis_text"], body_style))

    if "predictive_forecast" in report_data:
        story.append(Paragraph("Predictive Forecast", h3_style))
        story.append(Paragraph(report_data["predictive_forecast"], body_style))

    if "risk_assessment" in report_data:
        story.append(Paragraph("Risk Assessment Matrix", h3_style))
        story.append(Paragraph(report_data["risk_assessment"], body_style))
        
    if "key_insights" in report_data and report_data["key_insights"]:
        story.append(Paragraph("Key Findings", h2_style))
        for insight in report_data["key_insights"]:
            story.append(Paragraph(f"• {insight}", body_style))

    if "charts" in report_data and report_data["charts"] and isinstance(report_data["charts"], list):
        story.append(Paragraph("Analytical Visualizations", h2_style))
        async with httpx.AsyncClient(timeout=30.0) as client:
            for chart in report_data["charts"]:
                if not isinstance(chart, dict):
                    continue
                # Construct QuickChart payload
                qc_payload = {
                    "type": chart.get("type", "bar"),
                    "data": {
                        "labels": chart.get("labels", []),
                        "datasets": [{"label": "Metrics", "data": chart.get("data", [])}]
                    },
                    "options": {"title": {"display": True, "text": chart.get("title", "Chart")}, "legend": {"position": "bottom"}}
                }
                qc_url = f"https://quickchart.io/chart?c={urllib.parse.quote(json.dumps(qc_payload))}&w=500&h=300"
                try:
                    resp = await client.get(qc_url)
                    if resp.status_code == 200:
                        img_io = io.BytesIO(resp.content)
                        story.append(Image(img_io, width=400, height=240))
                        story.append(Spacer(1, 15))
                except Exception as e:
                    story.append(Paragraph(f"[Visualization {chart.get('title')} failed to render]", body_style))

    if "recommendations" in report_data and report_data["recommendations"]:
        story.append(Paragraph("Strategic Recommendations", h2_style))
        for rec in report_data["recommendations"]:
            story.append(Paragraph(f"• {rec}", body_style))
            
    if "conclusion" in report_data:
        story.append(Paragraph("Conclusion", h2_style))
        story.append(Paragraph(report_data["conclusion"], body_style))
        
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

async def execute_llm_prompt(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.GROK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(f"{settings.GROK_BASE_URL}/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception(f"LLM API Error: {response.text}")

async def generate_document_report(document_id: int, raw_text: str, filename: str, user_email: str = None, username: str = None):
    # Truncate text if it's too massive for standard context windows (just for safety in PoC)
    text_sample = raw_text[:20000] 

    try:
        # 1. Update DB Status to EXTRACTING
        db = SessionLocal()
        report = DocumentReport(document_id=document_id, status="EXTRACTING", progress_message="Extracting core context boundaries...")
        db.add(report)
        db.commit()
        db.refresh(report)
        
        await stream_manager.broadcast(document_id, "status", {"message": report.progress_message, "step": 1, "total": 5})

        # 2. Executive Summary & KPIs
        await stream_manager.broadcast(document_id, "status", {"message": "Synthesizing Executive Summary and Analytics...", "step": 2, "total": 5})
        report.progress_message = "Synthesizing Executive Summary and Analytics..."
        db.commit()

        prompt_1 = f"""
        You are a senior financial data analyst. You must analyze the following document text and output a STRICT JSON containing exact financial metrics.
        Document Name: {filename}
        Text: {text_sample}
        
        Extract these sections into a JSON object with this EXACT schema:
        {{
            "executive_summary": "A 1-paragraph short overview of the document",
            "kpis": [
                {{"label": "Total Revenue/Metric", "value": "$10M / 10%", "trend": "up/down/flat"}}
            ],
            "introduction": "Purpose and scope of the analysis",
            "data_overview": "What data this is"
        }}
        Output ONLY valid JSON. No markdown wrappers.
        """
        response_1 = await execute_llm_prompt(prompt_1)
        res_1_clean = response_1.replace('```json', '').replace('```', '').strip()
        data_1 = json.loads(res_1_clean)

        # 3. Deep Analysis & Trends
        await stream_manager.broadcast(document_id, "status", {"message": "Correlating trends and processing datasets...", "step": 3, "total": 5})
        report.progress_message = "Correlating trends and processing datasets..."
        db.commit()

        prompt_2 = f"""
        Based on the document text:
        {text_sample}
        
        Generate deep analysis and structured graph configurations for Chart.js.
        Return STRICT JSON format:
        {{
            "analysis_text": "Detailed trends, patterns, and correlations.",
            "predictive_forecast": "AI-driven forecast of future trends based on the current data.",
            "risk_assessment": "Comprehensive breakdown of risk matrices, anomalies, and outliers.",
            "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
            "recommendations": ["Rec 1", "Rec 2"],
            "conclusion": "Final thoughts",
            "charts": [
                {{
                    "type": "bar",
                    "title": "Category Comparison",
                    "labels": ["Cat A", "Cat B", "Cat C"],
                    "data": [10, 20, 30]
                }},
                {{
                    "type": "doughnut",
                    "title": "Distribution Clusters",
                    "labels": ["Segment 1", "Segment 2"],
                    "data": [40, 60]
                }},
                {{
                    "type": "radar",
                    "title": "Matrix Competency Assessment",
                    "labels": ["Metric 1", "Metric 2", "Metric 3", "Metric 4", "Metric 5"],
                    "data": [80, 90, 70, 85, 95]
                }}
            ]
        }}
        Output ONLY valid JSON.
        """
        response_2 = await execute_llm_prompt(prompt_2)
        res_2_clean = response_2.replace('```json', '').replace('```', '').strip()
        data_2 = json.loads(res_2_clean)

        # 4. Merge all JSON
        final_report = {**data_1, **data_2}
        
        await stream_manager.broadcast(document_id, "status", {"message": "Finalizing Document Format...", "step": 4, "total": 5})
        
        # 5. Save and Finish
        report.status = "COMPLETED"
        report.progress_message = "Analysis Complete!"
        report.report_json = json.dumps(final_report)
        report.updated_at = datetime.utcnow()
        db.commit()
        db.close()
        
        await stream_manager.broadcast(document_id, "status", {"message": "Analysis Complete!", "step": 5, "total": 5})
        await stream_manager.broadcast(document_id, "complete", {"status": "COMPLETED"})
        stream_manager.close(document_id)
        
        if user_email and username:
            try:
                pdf_buffer = await generate_pdf_report(final_report, filename)
                await send_report_ready_email(user_email, username, filename, document_id, pdf_buffer)
            except Exception as pdf_err:
                print(f"PDF generation failed, sending without attachment: {str(pdf_err)}")
                await send_report_ready_email(user_email, username, filename, document_id)

    except Exception as e:
        error_msg = str(e)
        print(f"Report Generation Failed: {error_msg}")
        try:
            db = SessionLocal()
            rep = db.query(DocumentReport).filter(DocumentReport.document_id == document_id).first()
            if rep:
                rep.status = "FAILED"
                rep.progress_message = f"Failed: {error_msg}"
                db.commit()
            db.close()
        except: pass
        await stream_manager.broadcast(document_id, "error", {"detail": error_msg})
        stream_manager.close(document_id)
