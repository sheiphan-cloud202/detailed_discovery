#!/usr/bin/env python3
"""
Cloud202 Executive Report Generator (Compliance-style runtime)
- Uses centralized BedrockConfig (inference profile + invoke_model like compliance_report.py)
- Keeps the Executive prompt/sections and tone
- Builds PDF with the same layout primitives as the compliance report
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import re
import argparse

# Centralized Bedrock configuration
from src.bedrock_config import BedrockConfig

# ReportLab & shared styles (same as compliance)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Shared canvas & styles (same as compliance)
from src.report_styles import EnhancedNumberedCanvas, create_enhanced_styles

# Configure logging (consistent with other generators)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Cloud202ExecutiveReportGenerator:
    """
    Executive Report Generator using the same Bedrock + PDF layout approach as the Compliance report.
    """

    def __init__(self, aws_region: str = None):
        # Use region from centralized config (mirrors compliance)
        self.aws_region = aws_region or BedrockConfig.get_region("executive")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use regional inference profile ARN (mirrors compliance)
        self.model_id = BedrockConfig.get_inference_profile_arn(self.aws_region)

        # Log the effective configuration
        BedrockConfig.log_configuration("executive", self.aws_region)

        # Create Bedrock client using centralized timeouts & retries (mirrors compliance)
        try:
            self.bedrock_runtime = BedrockConfig.create_bedrock_client(
                region=self.aws_region,
                report_type="executive"
            )
            logger.info("✅ AWS Bedrock client initialized for Executive report")
        except Exception as e:
            logger.warning(f"⚠️ Bedrock not available: {e}")
            self.bedrock_runtime = None

        # Token budget for executive reports (from BedrockConfig)
        self.max_tokens = BedrockConfig.get_token_limit("executive")

        # Output & styles
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)
        self.styles = create_enhanced_styles()

    # ---------- IO / Processing ----------

    def load_assessment_data(self, json_file_path: str) -> Dict[str, Any]:
        """Load customer assessment responses from JSON file."""
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"📖 Loaded assessment data from {json_file_path}")
        return data

    def process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process assessment data into a normalized dict used by prompts/PDF."""
        responses = raw_data.get('responses', {})

        # Company name heuristics (consistent with your other generators)
        business_owner = responses.get('business-owner', '')
        if ',' in business_owner:
            company_name = business_owner.split(',')[0].strip()
        else:
            company_name = responses.get('company-name', 'Valued Customer') or 'Valued Customer'

        processed_data = {
            'company_name': company_name,
            'industry': self._infer_industry(responses),
            'company_size': self._map_company_size(responses.get('scope-impact', '')),
            'assessment_type': responses.get('current-state', 'Exploratory'),
            'assessment_date': raw_data.get('exportDate', datetime.now().isoformat())[:10],
            'assessment_duration': self._map_timeline(responses.get('development-timeline', '')),
            'business_problem': responses.get('business-problems', ''),
            'budget_range': responses.get('budget-range', ''),
            'primary_goal': responses.get('primary-goal', ''),
            'strategic_alignment': responses.get('strategic-alignment', ''),
            'urgency': responses.get('urgency', ''),
            'responses': responses
        }
        return processed_data

    def _infer_industry(self, responses: Dict[str, Any]) -> str:
        """Infer industry from free-text answers."""
        problem = (responses.get('business-problems', '') or '').lower()

        if any(word in problem for word in ['clinical', 'physician', 'patient', 'healthcare', 'medical']):
            return 'Healthcare Technology'
        elif any(word in problem for word in ['financial', 'banking', 'fintech', 'payment', 'trading', 'market']):
            return 'Financial Technology'
        elif any(word in problem for word in ['vehicle', 'manufacturing', 'automotive']):
            return 'Manufacturing & Automotive'
        else:
            return 'Technology'

    def _map_company_size(self, scope: str) -> str:
        """Map scope text to size labels."""
        s = scope or ''
        if '200+' in s:
            return 'Mid-market (500-2000 employees)'
        elif '1000+' in s:
            return 'Enterprise (100,000+ employees)'
        elif '500+' in s:
            return 'Large Enterprise (2000-5000 employees)'
        else:
            return 'Enterprise'

    def _map_timeline(self, timeline: str) -> str:
        """Map development timeline to assessment duration."""
        t = timeline or ''
        if '3-6' in t:
            return '3 weeks'
        elif '6-12' in t:
            return '4 weeks'
        else:
            return '2 weeks'

    # ---------- Prompt ----------

    def create_executive_report_prompt(self, processed_data: Dict[str, Any]) -> str:
        """Create the executive prompt (unchanged in spirit; still JSON-only 6 sections)."""

        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        business_problem = processed_data.get('business_problem', '')
        primary_goal = processed_data.get('primary_goal', '')
        budget = processed_data.get('budget_range', '')
        urgency = processed_data.get('urgency', '')

        # ROI banding (same behavior as before)
        if '$500K' in budget or '$1M' in budget:
            roi, annual_savings, payback = '420% over 3 years', '$4.2M', '14 months'
        elif '$100K' in budget:
            roi, annual_savings, payback = '300% over 3 years', '$2.5M', '18 months'
        else:
            roi, annual_savings, payback = '350% over 3 years', '$3.2M', '16 months'

        prompt = f"""You are a senior Cloud202 Solutions Architect creating a comprehensive EXECUTIVE assessment report.

                COMPANY: {company_name}
                INDUSTRY: {industry}
                PRIMARY GOAL: {primary_goal}
                URGENCY: {urgency}

                ASSESSMENT DATA:
                {json.dumps(processed_data, indent=2)}

                Generate a detailed executive report with 6 sections. Each section should be 800-1200 words for a comprehensive 12-15 page PDF.

                CRITICAL: Return ONLY valid JSON with these exact keys:
                {{
                "executive_summary": "...",
                "business_case_analysis": "...",
                "technical_implementation_roadmap": "...",
                "financial_investment_analysis": "...",
                "risk_mitigation_strategy": "...",
                "strategic_recommendations": "..."
                }}

                SECTION REQUIREMENTS:

                1. EXECUTIVE SUMMARY (1-2 pages):
                - Business context for {company_name} in {industry}
                - Problem statement: {business_problem}
                - Proposed GenAI/Cloud solution overview
                - Expected outcomes and success metrics
                - Summary ROI: {roi}, Annual Savings: {annual_savings}, Payback: {payback}
                - 4-6 structured paragraphs

                2. BUSINESS CASE & VALUE PROPOSITION (2-3 pages):
                - Current state challenges and quantified impact
                - Target outcomes aligned to {primary_goal}
                - KPI tree (throughput, quality, cost, cycle time)
                - Org/people/process transformation narrative
                - Risk/benefit matrix with mitigations
                - 5-7 structured paragraphs

                3. TECHNICAL IMPLEMENTATION ROADMAP (2-3 pages):
                - Phased plan (0-3, 4-6, 7-9, 10-12 months)
                - Data, model, integration, and platform workstreams
                - Build vs buy decisions
                - Environments and release strategy
                - Dependencies and critical path
                - 5-7 structured paragraphs

                4. FINANCIAL INVESTMENT ANALYSIS (2 pages):
                - Budget bands derived from {budget}
                - Opex vs Capex, unit economics
                - ROI details beyond {roi}; sensitivity analysis
                - Licensing / cloud consumption assumptions
                - 3-5 structured paragraphs with numbers

                5. RISK MITIGATION STRATEGY (1-2 pages):
                - Delivery, security, privacy, and change risks
                - Controls and contingency plans
                - Governance and decision cadence
                - 3-4 structured paragraphs

                6. STRATEGIC RECOMMENDATIONS (1-2 pages):
                - Leadership & governance
                - Org readiness and capability model
                - Partnership strategy with Cloud202
                - Innovation & competitive positioning
                - AI CoE blueprint
                - 3-4 structured paragraphs

                FORMATTING RULES:
                - Professional business tone for C-level audience
                - Clear section headers (no markdown in the JSON)
                - Bullet points only when listing metrics or features
                - Provide concrete numbers, dates, and milestones
                - Total output should fit 12-15 PDF pages when rendered

                Return ONLY the JSON object with the 6 sections as keys. No markdown formatting, no code fences."""
        return prompt

    # ---------- Bedrock Invocation with Streaming ----------

    def generate_report_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate executive content using Bedrock streaming for incremental output."""
        if not self.bedrock_runtime:
            logger.warning("Bedrock runtime not available — using fallback content.")
            return self._generate_fallback_content(processed_data)

        prompt = self.create_executive_report_prompt(processed_data)

        try:
            logger.info("🤖 Generating executive report content (streaming)…")
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }

            # Stream tokens as they arrive
            stream = self.bedrock_runtime.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            assembled = []
            event_stream = stream.get("body")
            for event in event_stream:
                chunk = event.get("chunk")
                if not chunk:
                    continue
                try:
                    payload = json.loads(chunk.get("bytes").decode("utf-8"))
                except Exception:
                    # Fallback to raw decode if not JSON
                    payload = {"type": "text", "text": chunk.get("bytes").decode("utf-8", errors="ignore")}

                if isinstance(payload, dict):
                    # Bedrock text delta variants
                    text_piece = (
                        payload.get("delta", {}).get("text")
                        or payload.get("text")
                        or ""
                    )
                else:
                    text_piece = ""

                if text_piece:
                    assembled.append(text_piece)
                    # Lightweight preview log without overwhelming output
                    if len(assembled) % 20 == 0:
                        preview = text_piece.replace('\n', ' ')[:120]
                        logger.info(f"📝 Stream fragment: {preview}")

            content_text = "".join(assembled)
            content = self._parse_json_response(content_text)
            logger.info("✅ Executive content generated via streaming.")
            return content

        except Exception as e:
            logger.error(f"❌ Bedrock generation failed: {e}")
            logger.info("📋 Using high-quality fallback content...")
            return self._generate_fallback_content(processed_data)

    @staticmethod
    def _parse_json_response(text: str) -> Dict[str, Any]:
        """Remove code fences and parse JSON safely."""
        if not text:
            raise ValueError("Empty response content from Bedrock")
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()
        return json.loads(cleaned)

    # ---------- Fallback Content (keep high quality) ----------

    def _generate_fallback_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Executive fallback content with credible defaults (business-focused)."""
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        business_problem = processed_data.get('business_problem', 'operational challenges')
        budget = processed_data.get('budget_range', '$500K - $1M')

        return {
            'executive_summary': f"""EXECUTIVE SUMMARY

            {company_name} in the {industry} sector is evaluating a GenAI-enabled operating model to address {business_problem}.
            This initiative focuses on measurable outcomes: cycle-time reduction, cost-per-transaction reduction, and quality uplift,
            while improving governance and risk posture. The recommended plan targets 12–15 months to initial value realization,
            with an executive cadence of monthly steering and quarterly value checkpoints.""",

                        'business_case_analysis': f"""BUSINESS CASE & VALUE PROPOSITION

            The program quantifies benefits across throughput, quality, and costs. Assuming a {budget} investment envelope,
            the expected ROI over three years exceeds 300%, with accelerated payback once automation scales to priority workflows.
            Unit economics improve as volume grows and defect/leakage costs decline. A KPI tree links executive metrics to
            leading indicators such as first-pass yield, backlog age, and cycle time across value streams.""",

                        'technical_implementation_roadmap': """TECHNICAL IMPLEMENTATION ROADMAP

            Delivery follows a phased roadmap: discovery & baselining (0–30 days), pilot build & data enablement (31–90 days),
            scale-out & platform hardening (91–180 days), and enterprise rollout (180–360 days). Workstreams cover data,
            model lifecycle (eval/guardrails), integration, and platform operations with a secure-by-default approach.""",

                        'financial_investment_analysis': """FINANCIAL INVESTMENT ANALYSIS

            Budget considers platform subscriptions, cloud consumption, integration, change management, and enablement.
            A sensitivity analysis reflects utilization bands and workload seasonality. Assumptions include cloud credits,
            reserved capacity, and foundation investments that amortize across use cases.""",

                        'risk_mitigation_strategy': """RISK MITIGATION STRATEGY

            Primary risks include delivery slip, data quality, change fatigue, and model risk. Controls: gated releases,
            reference environments, backtesting, policy-as-code, and a clear RACI with escalation thresholds.
            A governance cadence enforces scope integrity and value tracking.""",

                        'strategic_recommendations': """STRATEGIC RECOMMENDATIONS

            Establish an Executive Steering Committee and an AI Center of Excellence, align incentives to outcome KPIs,
            adopt a product operating model, and prioritize two lighthouse use cases for rapid proof of value.
            Codify learnings into standards, templates, and enablement to accelerate the portfolio."""
        }

    # ---------- PDF Build (same layout primitives as compliance) ----------

    def create_title_page(self, styles, customer_data):
        """Create executive report title page (matching compliance report sophistication)"""
        elements = []
        
        # Add space at top
        elements.append(Spacer(1, 1.5 * inch))
        
        # Main title
        title = Paragraph("Executive Assessment Report", styles['TitleMain'])
        elements.append(title)
        elements.append(Spacer(1, 0.4 * inch))
        
        # Customer name
        company_name = customer_data.get("company_name", "")
        if company_name:
            customer_title = Paragraph(f"<b>{company_name}</b>", styles['TitleSub'])
            elements.append(customer_title)
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Details table with alternating row backgrounds
        details_data = [
            ['Industry:', customer_data.get('industry', 'Technology')],
            ['Assessment Type:', 'Executive Strategic'],
            ['Assessment Date:', customer_data.get('assessment_date', datetime.now().strftime('%Y-%m-%d'))],
            ['Duration:', customer_data.get('assessment_duration', '3 weeks')],
            ['Budget Range:', customer_data.get('budget_range', 'To be determined')]
        ]
        
        details_table = Table(details_data, colWidths=[2.2*inch, 2.8*inch])
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c5282')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#F8FAFB')]),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]))
        elements.append(details_table)
        
        elements.append(Spacer(1, 0.6 * inch))
        
        # Prepared for section
        prep_for_label = Paragraph("<b>Prepared for:</b>", styles['SectionHeading'])
        elements.append(prep_for_label)
        elements.append(Spacer(1, 0.08 * inch))
        prep_for_para = Paragraph(company_name, styles['BodyTextEnhanced'])
        elements.append(prep_for_para)
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Prepared by section
        branding = BedrockConfig.get_branding()
        prep_by_label = Paragraph("<b>Prepared by:</b>", styles['SectionHeading'])
        elements.append(prep_by_label)
        elements.append(Spacer(1, 0.08 * inch))
        prep_by_para = Paragraph(f"{branding['company_name']} Executive Advisory Team", styles['BodyTextEnhanced'])
        elements.append(prep_by_para)
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Confidentiality notice
        conf_text = f"<b>CONFIDENTIAL - {company_name} Strategic Assessment</b>"
        conf_para = Paragraph(conf_text, styles['TitleSub'])
        elements.append(conf_para)
        
        elements.append(Spacer(1, 0.2 * inch))
        
        # Report date
        date_para = Paragraph(
            f"Report Generated: {datetime.now().strftime('%B %d, %Y')}",
            styles['BodyTextEnhanced']
        )
        elements.append(date_para)
        
        elements.append(PageBreak())
        
        return elements

    def create_content_section(self, title: str, content: str, styles):
        """Create content section (matching compliance report intelligence)"""
        elements = []
        
        # Section title
        section_title = Paragraph(title, styles['MainHeading'])
        elements.append(section_title)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Process content
        if content.strip():
            # Split into paragraphs
            paragraphs = content.split('\n\n')
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # Skip if paragraph matches section title (avoid duplicate)
                if para == title:
                    continue
                
                # Check if it's a subsection header
                is_subsection = para.endswith(':') or (
                    len(para.split()) <= 8 and para[0].isupper() and len(para) < 80
                )
                
                if is_subsection:
                    # Subsection heading
                    subsection = Paragraph(para, styles['SectionHeading'])
                    elements.append(subsection)
                    elements.append(Spacer(1, 0.08 * inch))
                else:
                    # Regular paragraph
                    paragraph = Paragraph(para, styles['BodyTextEnhanced'])
                    elements.append(paragraph)
                    elements.append(Spacer(1, 0.1 * inch))
        
        # Always end with page break for dedicated pages
        if elements and len(elements) > 2:
            elements.append(PageBreak())
        
        return elements

    def build_pdf(self, content: Dict[str, str], output_path: Path) -> None:
        """Render the Executive report content into a styled PDF (matching compliance sophistication)."""
        processed_data = self.process_assessment_data({'responses': {}}) if not hasattr(self, '_current_processed_data') else self._current_processed_data
        
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=0.7 * inch,
            leftMargin=0.7 * inch,
            topMargin=0.7 * inch,
            bottomMargin=1 * inch,
            title=f"Executive Assessment - {processed_data.get('company_name', 'Customer')}",
            author="Cloud202 Executive Team"
        )
        
        styles = create_enhanced_styles()
        elements = []
        
        # Sophisticated title page
        elements.extend(self.create_title_page(styles, processed_data))
        
        # Content sections using sophisticated formatting
        sections = [
            ("Executive Summary", content.get('executive_summary', '')),
            ("Business Case & Value Proposition", content.get('business_case_analysis', '')),
            ("Technical Implementation Roadmap", content.get('technical_implementation_roadmap', '')),
            ("Financial Investment Analysis", content.get('financial_investment_analysis', '')),
            ("Risk Mitigation Strategy", content.get('risk_mitigation_strategy', '')),
            ("Strategic Recommendations", content.get('strategic_recommendations', ''))
        ]
        
        for title, text in sections:
            elements.extend(self.create_content_section(title, text, styles))
        
        # Build PDF with EnhancedNumberedCanvas
        def make_canvas(*args, **kwargs):
            branding = BedrockConfig.get_branding()
            return EnhancedNumberedCanvas(
                *args,
                company_name=processed_data.get('company_name', branding.get('company_name', 'Cloud202')),
                report_type='Executive Assessment',
                **kwargs
            )
        
        doc.build(elements, canvasmaker=make_canvas)
        logger.info(f"📄 PDF written: {output_path}")

    # ---------- Orchestration ----------

    def generate_report(self, json_file_path: str) -> Dict[str, Any]:
        """End-to-end: load → process → generate → render PDF."""
        raw = self.load_assessment_data(json_file_path)
        processed = self.process_assessment_data(raw)
        content = self.generate_report_content(processed)

        # Store processed data for PDF generation
        self._current_processed_data = processed

        safe_company = re.sub(r'[^A-Za-z0-9_-]+', '_', processed.get('company_name', 'Customer')).strip('_')
        pdf_path = self.output_dir / f"Executive_Report_{safe_company}_{self.timestamp}.pdf"
        self.build_pdf(content, pdf_path)

        return {
            "pdf_path": str(pdf_path),
            "content": content,
            "meta": processed
        }


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Generate Executive Report (compliance-style runtime).")
    parser.add_argument("input_json", help="Path to assessment JSON export")
    parser.add_argument("--region", help="AWS region (overrides BedrockConfig default for executive)", default=None)
    args = parser.parse_args()

    gen = Cloud202ExecutiveReportGenerator(aws_region=args.region)
    result = gen.generate_report(args.input_json)

    print(json.dumps({
        "ok": True,
        "pdf_path": result["pdf_path"],
        "meta": result["meta"]
    }, indent=2))


if __name__ == "__main__":
    main()
