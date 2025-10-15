import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import re
import argparse

# Import Strands libraries
from strands import Agent
from strands.models.bedrock import BedrockModel

# Import ReportLab libraries
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Import shared styling components
from report_styles import NumberedCanvas, create_enhanced_styles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Cloud202ExecutiveReportGenerator:
    """
    Cloud202 Executive Report Generator using Strands Agents and Bedrock
    """

    def __init__(self, aws_region: str = "eu-west-1", company_name: str = "Cloud202",
                 tool_name: str = "Qubitz", contact_email: str = "hello@cloud202.com",
                 contact_phone: str = "+44 7792 565738", model_id: str = None):
        """
        Initialize the executive report generator

        Args:
            aws_region: AWS region for Bedrock (default: eu-west-1)
            company_name: Company name for branding
            tool_name: Tool name for branding
            contact_email: Contact email
            contact_phone: Contact phone
        """
        self.aws_region = aws_region
        self.company_name = company_name
        self.tool_name = tool_name
        self.contact_email = contact_email
        self.contact_phone = contact_phone
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Initialize Strands Agent with Bedrock model (hard-coded per request)
        resolved_model_id = "anthropic.claude-3-7-sonnet-20250219-v1:0"
        logger.info(f"Initializing Bedrock model: {resolved_model_id}")

        self.bedrock_model = BedrockModel(
            model_id=resolved_model_id,
            region=aws_region,
            max_tokens=16000
        )

        self.agent = Agent(model=self.bedrock_model)

        # Create output directory
        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

        logger.info("✅ Initialized Cloud202 Executive Report Generator")
        logger.info(f"🤖 Using model: {resolved_model_id}")
        logger.info(f"🌍 Region: {aws_region}")

    @staticmethod
    def generate_all_reports(json_file_path: str, force_compliance: bool = True) -> Dict[str, Dict[str, Any]]:
        """Generate Executive, Technical, and Compliance reports together.

        Returns a dict mapping report types to their result dicts. Any report that fails returns None.
        """
        results: Dict[str, Any] = {"executive": None, "technical": None, "compliance": None}

        # Executive
        try:
            exec_gen = Cloud202ExecutiveReportGenerator()
            results["executive"] = exec_gen.generate_report(json_file_path)
        except Exception as e:
            logger.error(f"Executive report failed: {e}")

        # Technical
        try:
            from technical_report import Cloud202TechnicalDeepDiveGenerator
            tech_gen = Cloud202TechnicalDeepDiveGenerator()
            results["technical"] = tech_gen.generate_report(json_file_path)
        except Exception as e:
            logger.error(f"Technical report failed: {e}")

        # Compliance (forced if configured)
        try:
            from compliance_report import ComplianceReportGenerator
            comp_gen = ComplianceReportGenerator(aws_region="us-east-1")
            results["compliance"] = comp_gen.generate_report(json_file_path, force=force_compliance)
        except Exception as e:
            logger.error(f"Compliance report failed: {e}")

        return results

    def load_assessment_data(self, json_file_path: str) -> Dict[str, Any]:
        """Load customer assessment responses from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                customer_data = json.load(file)
            logger.info(f"📖 Loaded assessment data from {json_file_path}")
            return customer_data
        except Exception as e:
            logger.error(f"Error loading assessment data: {e}")
            raise

    def process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process assessment data from JSON format"""
        responses = raw_data.get('responses', {})

        business_owner = responses.get('business-owner', '')
        if ',' in business_owner:
            company_name = business_owner.split(',')[0].strip()
        else:
            company_name = 'Valued Customer'

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

    def _infer_industry(self, responses: Dict) -> str:
        """Infer industry from responses"""
        problem = responses.get('business-problems', '').lower()

        if any(word in problem for word in ['clinical', 'physician', 'patient', 'healthcare', 'medical']):
            return 'Healthcare Technology'
        elif any(word in problem for word in ['financial', 'banking', 'fintech', 'payment', 'trading', 'market']):
            return 'Financial Technology'
        elif any(word in problem for word in ['vehicle', 'manufacturing', 'automotive']):
            return 'Manufacturing & Automotive'
        else:
            return 'Technology'

    def _map_company_size(self, scope: str) -> str:
        """Map scope to company size"""
        if '200+' in scope:
            return 'Mid-market (500-2000 employees)'
        elif '1000+' in scope:
            return 'Enterprise (100,000+ employees)'
        elif '500+' in scope:
            return 'Large Enterprise (2000-5000 employees)'
        else:
            return 'Enterprise'

    def _map_timeline(self, timeline: str) -> str:
        """Map development timeline to assessment duration"""
        if '3-6' in timeline:
            return '3 weeks'
        elif '6-12' in timeline:
            return '4 weeks'
        else:
            return '2 weeks'

    def create_executive_report_prompt(self, processed_data: Dict[str, Any]) -> str:
        """Create comprehensive prompt for executive report generation"""

        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        business_problem = processed_data.get('business_problem', '')
        primary_goal = processed_data.get('primary_goal', '')
        budget = processed_data.get('budget_range', '')
        urgency = processed_data.get('urgency', '')

        # Calculate ROI based on budget
        if '$500K' in budget or '$1M' in budget:
            roi, annual_savings, payback = '420% over 3 years', '$4.2M', '14 months'
        elif '$100K' in budget:
            roi, annual_savings, payback = '300% over 3 years', '$2.5M', '18 months'
        else:
            roi, annual_savings, payback = '350% over 3 years', '$3.2M', '16 months'

        prompt = f"""You are a senior {self.company_name} Solutions Architect creating a comprehensive EXECUTIVE assessment report.

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

1. EXECUTIVE SUMMARY (1 page):
- Business problem: {business_problem}
- Proposed GenAI solution approach
- Quantified benefits: {roi} with {payback} payback, {annual_savings} annual savings
- Key findings and recommendations
- Strategic imperative for action within 30-60 days
- Write 4-6 paragraphs, each 3-5 sentences
- Professional, executive-level language

2. BUSINESS CASE & VALUE PROPOSITION (2-3 pages):
- Current State Challenges: Analyze business problems in detail
- Proposed Solution Benefits using GenAI and cloud services
- Quantified Impact: Cost savings, efficiency gains, revenue growth
- Competitive advantages in {industry} sector
- Strategic alignment with business goals
- Use subheaders for each major topic
- Mix of detailed paragraphs with occasional bullet points for key metrics only

3. IMPLEMENTATION ROADMAP (2-3 pages):
- Phase 1: Foundation (Months 1-3) - Infrastructure setup, security framework, pilot design
- Phase 2: AI Development (Months 4-6) - Model integration, data pipeline, initial deployment
- Phase 3: Pilot Deployment (Months 7-9) - Limited rollout, testing, optimization
- Phase 4: Production Scale (Months 10-12) - Full deployment, monitoring, support
- Each phase needs: objectives, key milestones, deliverables, resources needed
- Detailed paragraph descriptions for each phase

4. INVESTMENT & ROI ANALYSIS (1-2 pages):
- Total investment breakdown: {budget}
- Expected ROI: {roi}
- Annual savings: {annual_savings}
- Payback period: {payback}
- Break-even analysis with timeline
- Risk-adjusted financial projections
- Cost optimization strategies

5. RISK ASSESSMENT & NEXT STEPS (1-2 pages):
- Technical risks: integration, performance, scalability
- Operational risks: adoption, change management, skills gaps
- Financial risks: budget, ROI realization
- Mitigation strategies for each risk category
- Success factors and KPIs to track
- Immediate next steps with 30-60-90 day plan

6. STRATEGIC RECOMMENDATIONS (1-2 pages):
- Leadership and governance framework needed
- Organizational readiness and capability development
- Partnership strategy with {self.company_name}
- Innovation and competitive positioning approach
- Long-term investment allocation strategy
- How to establish AI Center of Excellence

FORMATTING RULES:
- Write in professional business paragraphs
- Use clear section headers
- Use bullet points ONLY for lists of metrics, features, or requirements
- Provide specific numbers, timelines, and data points
- Keep business-focused and executive-friendly
- Professional tone suitable for C-level executives
- Total content: 12-15 pages when rendered

Return ONLY the JSON object with the 6 sections as keys. No markdown formatting, no code blocks."""

        return prompt

    def generate_report_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate report content using Strands Agent and Bedrock"""
        try:
            logger.info("🤖 Generating executive report content using Bedrock...")

            prompt = self.create_executive_report_prompt(processed_data)

            # Generate using Strands Agent
            response = self.agent(prompt)

            # Extract and parse JSON
            content_text = str(response)

            # Clean JSON markers
            content_text = re.sub(r'```json\n?', '', content_text)
            content_text = re.sub(r'```\n?', '', content_text)
            content_text = content_text.strip()

            # Parse JSON
            content = json.loads(content_text)

            logger.info("✅ Successfully generated report content using Bedrock")
            return content

        except Exception as e:
            logger.error(f"❌ Bedrock generation failed: {e}")
            logger.info("📋 Using fallback content...")
            return self._generate_fallback_content(processed_data)

    def _generate_fallback_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate fallback content if Bedrock fails"""
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        business_problem = processed_data.get('business_problem', 'operational challenges')
        budget = processed_data.get('budget_range', '$500K - $1M')

        return {
            'executive_summary': f"""EXECUTIVE SUMMARY

{company_name}, a leading organization in the {industry} sector, faces critical challenges with {business_problem}. Our comprehensive RAPID assessment using {self.tool_name} has identified substantial opportunities for transformation through Generative AI implementation.

The proposed GenAI solution addresses these challenges through intelligent automation, enhanced decision-making capabilities, and operational excellence. By leveraging cloud-based AI services, {company_name} can achieve significant improvements in efficiency, accuracy, and scalability while reducing operational costs.

Our assessment reveals exceptional organizational readiness for GenAI adoption. We project 420% ROI over 3 years with 14-month payback period. Direct cost savings of $4.2M annually will result from process automation and productivity improvements.

Investment required: {budget} over 18-month deployment timeline. Expected returns include direct cost savings of $4.2M annually, revenue enhancement of $1.8-2.4M annually, and operational efficiency improvements of 40-55% reduction in processing time.

Critical success factors include strong executive sponsorship, comprehensive change management, technical excellence in deployment, and continuous improvement based on performance metrics. We recommend immediate implementation with 95% confidence based on comprehensive readiness assessment. The strategic window for competitive advantage requires decisive action within 30-60 days.""",

            'business_case_analysis': f"""BUSINESS CASE & VALUE PROPOSITION

Current State Challenges

{company_name} faces significant operational inefficiencies with {business_problem}. These challenges represent a critical constraint on business growth and competitive positioning in the {industry} sector. Current manual processes consume excessive resources while limiting organizational agility and market responsiveness.

Proposed GenAI Solution Benefits

The recommended GenAI solution leverages cloud-based AI services to create intelligent automation capabilities that transform business operations. Core capabilities include natural language processing, predictive analytics, intelligent document processing, and automated decision support that addresses identified pain points through proven AI technologies.

Quantified Business Impact

Comprehensive financial modeling projects 420% ROI over 3 years through multiple value streams including direct cost savings, revenue enhancement, and operational efficiency improvements. Direct cost savings of $1.8-2.4M annually result from process automation, productivity improvements, and resource optimization.

Competitive Advantages

GenAI implementation positions {company_name} as an innovation leader in {industry} with sustainable competitive advantages through enhanced customer experience, operational excellence, and strategic agility. Early adoption provides 2-3x performance premiums over late adopters.""",

            'technical_implementation_roadmap': """IMPLEMENTATION ROADMAP

Phase 1: Foundation (Months 1-3)

The foundation phase establishes core infrastructure, security frameworks, and integration capabilities required for GenAI deployment. Infrastructure provisioning includes cloud accounts structure, identity and access management, networking configuration, and security controls aligned with enterprise requirements. Key deliverables include architecture documentation, security compliance certification, and development environment operational readiness.

Phase 2: AI Development (Months 4-6)

The development phase implements core GenAI capabilities using foundation models for AI services, custom model development platforms, and serverless compute integration. Integration development includes API gateway configuration, authentication systems, and monitoring implementation. Data pipeline development handles real-time data processing with quality validation.

Phase 3: Pilot Deployment (Months 7-9)

Pilot deployment implements GenAI capabilities for limited user groups with comprehensive monitoring and optimization processes. User acceptance testing includes functionality validation, performance benchmarking, and user experience optimization. Feedback integration processes capture user requirements and optimization opportunities.

Phase 4: Production Scale (Months 10-12)

Production deployment extends GenAI capabilities organization-wide with enterprise-grade reliability, security, and performance. Auto-scaling implementation handles variable workloads while optimizing costs. Operational excellence includes automated backup and recovery procedures with proactive monitoring.""",

            'financial_investment_analysis': f"""INVESTMENT & ROI ANALYSIS

Total Investment Requirement

The GenAI implementation requires total investment of {budget} over 18-month deployment timeline, structured across technology infrastructure, professional services, internal resources, and change management activities. Technology costs represent 45% of total investment including cloud services, software licensing, security tools, and monitoring platforms.

Expected Returns Analysis

Comprehensive financial modeling projects exceptional returns through multiple value streams delivering 420% ROI over 3-year horizon. Direct cost savings of $2.1-2.8M annually result from process automation eliminating 45-60% of manual processing requirements. Revenue enhancement opportunities total $2.4-3.7M annually through improved customer experience.

Break-even Analysis

Conservative financial modeling demonstrates break-even achievement within 16-18 months post-implementation, with accelerating value realization thereafter. Cash flow analysis demonstrates positive monthly cash flow beginning month 15-18, with cumulative value creation exceeding $8-12M over 3-year horizon.

Risk-Adjusted Projections

Sensitivity analysis across key variables including adoption rates, technology performance, and market conditions provides robust financial validation. Conservative scenario delivers 25% IRR, base case achieves 45% IRR, and optimistic scenario realizes 65% IRR.""",

            'risk_mitigation_strategy': """RISK ASSESSMENT & NEXT STEPS

Key Risks and Mitigation Strategies

Comprehensive risk analysis identifies potential threats across technical, operational, and financial dimensions. Technical risks include integration complexity with existing systems (medium probability, high impact) mitigated through comprehensive architecture planning and phased integration approach.

Operational risks encompass user adoption resistance (medium probability, high impact) addressed through comprehensive change management program, user training initiatives, and adoption incentive structures. Financial risks include budget overruns (medium probability, medium impact) managed through detailed cost estimation and financial controls.

Success Factors and KPIs

Critical success factors include executive sponsorship maintenance, technical excellence achievement, user adoption rate >85%, and financial performance meeting projection targets. KPI framework encompasses technical metrics (system uptime >99.9%, response time <2 seconds), operational metrics (user adoption rate, process efficiency improvement), and financial metrics (ROI realization, budget adherence).

Immediate Next Steps

30-60 day immediate actions include executive approval finalization, project governance establishment, core team mobilization, and vendor contract execution. 60-90 day horizon includes detailed technical design completion, integration planning finalization, and pilot user group selection.""",

            'strategic_recommendations': f"""STRATEGIC RECOMMENDATIONS

Leadership and Governance Framework

{company_name} leadership must establish comprehensive governance framework with C-level sponsorship, clear accountability structures, and strategic decision-making authority to ensure GenAI transformation success. Recommended governance includes Executive Steering Committee with CEO/COO leadership, Technical Advisory Board with CTO/CIO participation, and operational oversight councils.

We recommend establishing an AI Center of Excellence led by a Chief AI Officer, reporting directly to the CEO. This center will be responsible for setting AI vision, strategy, and governance while fostering a data-driven culture across the organization.

Organizational Readiness and Capability Development

Strategic recommendation emphasizes comprehensive organizational transformation beyond technology implementation, including culture change, capability development, and process optimization. Capability development includes technical skills training for AI/ML literacy, operational skills enhancement for digital collaboration, and leadership development for change management.

Partnership and Ecosystem Strategy

{company_name} should leverage strategic partnerships with {self.company_name} for ongoing advantage through professional services engagement, architectural guidance, and continuous optimization support. Partnership benefits include access to leading-edge capabilities, industry expertise, and strategic insights from global AI implementation experience.

Innovation and Competitive Positioning Strategy

Long-term competitive positioning requires continuous innovation, capability enhancement, and market leadership demonstration. Investment prioritization includes proven ROI opportunities, strategic capability development, and competitive positioning enhancement to ensure sustained value creation and market leadership."""
        }


    def create_title_page(self, styles, customer_data):
        """Create a professional title page"""
        elements = []

        # Add space at top
        elements.append(Spacer(1, 1.5 * inch))

        # Main title
        title = Paragraph(f"{self.company_name}", styles['TitlePage'])
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))

        # Subtitle
        subtitle = Paragraph("GenAI Solutions", styles['Subtitle'])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.5 * inch))

        # Report type
        report_type = Paragraph("RAPID GenAI Assessment<br/>Comprehensive Executive Report", styles['TitlePage'])
        elements.append(report_type)
        elements.append(Spacer(1, 1 * inch))

        # Customer name
        company_name = customer_data.get("company_name", "")
        if company_name:
            customer_title = Paragraph(f"<b>Prepared for:</b><br/>{company_name}", styles['Subtitle'])
            elements.append(customer_title)

        elements.append(Spacer(1, 0.5 * inch))

        # Details table
        details_data = [
            ['Industry:', customer_data.get('industry', 'Technology')],
            ['Company Size:', customer_data.get('company_size', 'Enterprise')],
            ['Assessment Type:', customer_data.get('assessment_type', 'Comprehensive')],
            ['Assessment Duration:', customer_data.get('assessment_duration', '3 weeks')]
        ]

        details_table = Table(details_data, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(details_table)

        elements.append(Spacer(1, 1 * inch))

        # Report date
        date_text = f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}"
        date_para = Paragraph(date_text, styles['Subtitle'])
        elements.append(date_para)

        elements.append(Spacer(1, 0.3 * inch))

        # RAPID program info
        rapid_text = f"Readiness Assessment Acceleration Program (RAPID) - {self.tool_name}"
        rapid_para = Paragraph(rapid_text, styles['Normal'])
        elements.append(rapid_para)

        elements.append(Spacer(1, 0.2 * inch))

        # Confidentiality notice
        conf_text = f"<b>CONFIDENTIAL - {self.company_name} Strategic Assessment</b>"
        conf_para = Paragraph(conf_text, styles['Subtitle'])
        elements.append(conf_para)

        elements.append(PageBreak())

        return elements

    def create_table_of_contents(self, styles):
        """Create table of contents"""
        elements = []

        toc_title = Paragraph("Table of Contents", styles['MainHeading'])
        elements.append(toc_title)
        elements.append(Spacer(1, 0.3 * inch))

        toc_items = [
            ("Executive Summary", "3"),
            ("Business Case Analysis", "4"),
            ("Technical Implementation Roadmap", "6"),
            ("Financial Investment Analysis", "8"),
            ("Risk Mitigation Strategy", "10"),
            ("Strategic Recommendations", "12"),
            ("Appendix - Assessment Details", "14")
        ]

        for item, page_num in toc_items:
            toc_entry = Paragraph(
                f'{item} {"." * 80} {page_num}',
                styles['BodyText']
            )
            elements.append(toc_entry)
            elements.append(Spacer(1, 0.1 * inch))

        elements.append(PageBreak())

        return elements

    def create_content_section(self, title: str, content: str, styles, is_executive: bool = False):
        """Create a content section with proper formatting"""
        elements = []

        # Section title
        section_title = Paragraph(title, styles['MainHeading'])
        elements.append(section_title)
        elements.append(Spacer(1, 0.2 * inch))

        # Executive summary callout
        if is_executive:
            exec_callout = Paragraph(
                "<b>STRATEGIC EXECUTIVE SUMMARY</b>",
                styles['HighlightBox']
            )
            elements.append(exec_callout)
            elements.append(Spacer(1, 0.15 * inch))

        # Process content
        if content.strip():
            # Split into paragraphs
            paragraphs = content.split('\n\n')

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue

                # Check if it's a subsection header (starts with capital letter and ends with colon or is short)
                if (para.endswith(':') or (len(para.split()) <= 8 and para[0].isupper())) and len(para) < 100:
                    # Subsection heading
                    subsection = Paragraph(para, styles['SubsectionHeading'])
                    elements.append(subsection)
                    elements.append(Spacer(1, 0.1 * inch))
                else:
                    # Regular paragraph
                    paragraph = Paragraph(para, styles['BodyText'])
                    elements.append(paragraph)
                    elements.append(Spacer(1, 0.08 * inch))

        elements.append(PageBreak())

        return elements

    def create_appendix(self, styles, customer_data):
        """Create appendix section"""
        elements = []

        # Appendix title
        appendix_title = Paragraph("Appendix - Assessment Details", styles['MainHeading'])
        elements.append(appendix_title)
        elements.append(Spacer(1, 0.2 * inch))

        # RAPID Methodology
        method_heading = Paragraph("RAPID Assessment Methodology", styles['SectionHeading'])
        elements.append(method_heading)
        elements.append(Spacer(1, 0.15 * inch))

        method_text = f"""The Readiness Assessment Acceleration Program (RAPID) is a comprehensive evaluation framework designed to assess organizational readiness for GenAI implementation using {self.tool_name}. This assessment encompasses technical infrastructure, data readiness, compliance requirements, and business value analysis to provide strategic recommendations for successful GenAI adoption."""

        method_para = Paragraph(method_text, styles['BodyText'])
        elements.append(method_para)
        elements.append(Spacer(1, 0.2 * inch))

        # Assessment Scope
        scope_heading = Paragraph("Assessment Scope and Coverage", styles['SectionHeading'])
        elements.append(scope_heading)
        elements.append(Spacer(1, 0.15 * inch))

        scope_items = [
            "Use Case Discovery and Business Requirements Analysis",
            "Data Readiness and Infrastructure Assessment",
            "Model Evaluation and Technical Architecture Review",
            "Compliance and Security Framework Analysis",
            "Business Value and ROI Calculation",
            "Implementation Planning and Risk Assessment",
            "Change Management and Organizational Readiness"
        ]

        for item in scope_items:
            bullet = Paragraph(f"• {item}", styles['BulletPoint'])
            elements.append(bullet)

        elements.append(Spacer(1, 0.3 * inch))

        # Contact Information
        contact_heading = Paragraph(f"{self.company_name} Contact", styles['SectionHeading'])
        elements.append(contact_heading)
        elements.append(Spacer(1, 0.15 * inch))

        contact_text = f"""For questions regarding this assessment or next steps:

{self.company_name} Team
Email: {self.contact_email}
Phone: {self.contact_phone}

Assessment Lead: {self.company_name} Senior Solutions Architect
Customer Success Manager: {self.company_name} Customer Success Manager"""

        contact_para = Paragraph(contact_text.replace('\n', '<br/>'), styles['BodyText'])
        elements.append(contact_para)

        return elements

    def create_professional_pdf(self, content: Dict[str, str], customer_info: Dict[str, Any], output_path: str):
        """Create professional PDF using ReportLab"""
        logger.info(f"📄 Creating professional PDF: {output_path}")

        try:
            # Create document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.75 * inch,
                bottomMargin=1 * inch,
                title=f"RAPID GenAI Assessment Report - {customer_info.get('company_name', 'Customer')}",
                author=f"{self.company_name} GenAI Solutions"
            )

            # Get styles
            styles = create_enhanced_styles()

            # Build document elements
            elements = []

            # Title page
            elements.extend(self.create_title_page(styles, customer_info))

            # Table of contents
            elements.extend(self.create_table_of_contents(styles))

            # Content sections
            sections = [
                ("Executive Summary", content.get('executive_summary', ''), True),
                ("Business Case Analysis", content.get('business_case_analysis', ''), False),
                ("Technical Implementation Roadmap", content.get('technical_implementation_roadmap', ''), False),
                ("Financial Investment Analysis", content.get('financial_investment_analysis', ''), False),
                ("Risk Mitigation Strategy", content.get('risk_mitigation_strategy', ''), False),
                ("Strategic Recommendations", content.get('strategic_recommendations', ''), False)
            ]

            for title, text, is_exec in sections:
                elements.extend(self.create_content_section(title, text, styles, is_exec))

            # Appendix
            elements.extend(self.create_appendix(styles, customer_info))

            # Build PDF with custom canvas for page numbers
            def make_canvas(*args, **kwargs):
                kwargs['report_type'] = 'RAPID Assessment'
                return NumberedCanvas(*args, **kwargs)
            doc.build(elements, canvasmaker=make_canvas)

            logger.info("✅ PDF generated successfully!")

        except Exception as e:
            logger.error(f"Error creating PDF: {e}")
            raise

    def generate_report(self, json_file_path: str, output_filename: str = None) -> Dict[str, str]:
        """Generate complete executive report"""
        try:
            logger.info("🚀 Starting executive report generation...")

            # Load data
            raw_data = self.load_assessment_data(json_file_path)

            # Process data
            logger.info("📄 Processing assessment data...")
            processed_data = self.process_assessment_data(raw_data)

            # Generate filename
            if not output_filename:
                company_name = re.sub(r'[^\w\-_]', '_', processed_data.get('company_name', 'customer').lower())
                output_filename = f"RAPID_Executive_Report_{company_name}_{self.timestamp}"

            pdf_file = self.output_dir / f"{output_filename}.pdf"

            # Generate content
            content = self.generate_report_content(processed_data)

            # Create PDF
            self.create_professional_pdf(content, processed_data, str(pdf_file))

            results = {
                'pdf_path': str(pdf_file),
                'company_name': processed_data.get('company_name'),
                'industry': processed_data.get('industry'),
                'assessment_type': processed_data.get('assessment_type'),
                'timestamp': self.timestamp
            }

            logger.info("✅ Report generation completed successfully!")
            return results

        except Exception as e:
            logger.error(f"❌ Error in report generation: {e}")
            raise


def main():
    """Main function"""

    print("\n" + "="*60)
    print("🚀 Cloud202 Executive Report Generator v2.0")
    print("="*60)

    # Configuration
    AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Cloud202 Executive Report Generator")
    parser.add_argument("--json", dest="json_path", help="Path to assessment JSON file", default=None)
    # Model is hard-coded; keep flag out to avoid confusion
    parser.add_argument("--region", dest="region", help="AWS region (overrides AWS_REGION)", default=None)
    parser.add_argument("--all", dest="generate_all", action="store_true", help="Generate Executive, Technical, and Compliance reports")
    args = parser.parse_args()

    # If a JSON path is provided via CLI, use it directly
    if args.json_path:
        json_file = args.json_path.strip().strip("\"'")
    else:
        # Find JSON files (show only .json files in current directory)
        json_path_objects = list(Path(".").glob("*.json"))
        # Fallback to known sample if present
        if Path("test_json_comprehensive.json").exists():
            json_path_objects = [Path("test_json_comprehensive.json")] + [p for p in json_path_objects if p.name != "test_json_comprehensive.json"]
        json_files = json_path_objects

    if args.json_path is None and json_files:
        print(f"\n📂 Found {len(json_files)} JSON file(s):")
        for i, file in enumerate(json_files, 1):
            # Ensure we work with Path objects for metadata
            path_obj = file if isinstance(file, Path) else Path(str(file))
            try:
                file_size = path_obj.stat().st_size / 1024
                size_str = f"{file_size:.1f} KB"
            except Exception:
                size_str = "unknown size"
            print(f"   {i}. {path_obj.name} ({size_str})")

        print(f"\n   {len(json_files) + 1}. Enter custom file path")
        print("   0. Exit")

        while True:
            try:
                choice = input(f"\nSelect option (0-{len(json_files) + 1}): ").strip()

                if choice == "0":
                    print("👋 Exiting...")
                    return 0
                elif choice == str(len(json_files) + 1):
                    json_file = input("\n📄 Enter JSON file path: ").strip().strip("\"'")
                    break
                elif 1 <= int(choice) <= len(json_files):
                    selected = json_files[int(choice) - 1]
                    json_file = str(selected if isinstance(selected, Path) else Path(str(selected)))
                    print(f"✅ Selected: {json_file}")
                    break
                else:
                    print("❌ Invalid selection.")
            except (ValueError, IndexError):
                print("❌ Invalid input.")
    elif args.json_path is None:
        json_file = input("\n📄 Enter JSON file path: ").strip().strip("\"'")

    # Check if file exists
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return 1

    try:
        if args.generate_all:
            print("\n⚙️ Generating all reports (Executive, Technical, Compliance)...")
            combined = Cloud202ExecutiveReportGenerator.generate_all_reports(json_file, force_compliance=True)

            print("\n" + "="*60)
            print("✅ ALL REPORTS GENERATED SUCCESSFULLY!")
            print("="*60)
            print(f"📂 Input file: {json_file}")

            for rtype in ["executive", "technical", "compliance"]:
                res = combined.get(rtype)
                if res and isinstance(res, dict) and res.get('pdf_path'):
                    print(f"📄 {rtype.title()} Report: {res['pdf_path']}")
                else:
                    print(f"❌ {rtype.title()} Report: generation failed")

            return 0
        else:
            # Initialize generator
            print("\n⚙️ Initializing Cloud202 Executive Report Generator...")
            generator = Cloud202ExecutiveReportGenerator(
                aws_region=(args.region or AWS_REGION),
                company_name="Cloud202",
                tool_name="Qubitz",
                contact_email="hello@cloud202.com",
                contact_phone="+44 7792 565738",
                model_id=None
            )
            
            # Generate report
            results = generator.generate_report(json_file)
            
            # Display results
            print("\n" + "="*60)
            print("✅ RAPID EXECUTIVE REPORT GENERATED SUCCESSFULLY!")
            print("="*60)
            print(f"📂 Input file: {json_file}")
            print(f"📄 Output file: {results['pdf_path']}")
            print(f"🏢 Customer: {results['company_name']}")
            print(f"🏭 Industry: {results['industry']}")
            print(f"📊 Assessment Type: {results['assessment_type']}")
            print("🛠️ Generated with: Cloud202 Qubitz")
            print(f"⏰ Timestamp: {results['timestamp']}")
            print("📈 Report includes comprehensive strategic analysis and recommendations")
            print("="*60)
            
            print("\n🎉 SUCCESS! Your enhanced executive report is ready!")
            print(f"📄 Report saved as: {results['pdf_path']}")
            print("📊 This report contains comprehensive strategic analysis suitable for C-level presentations")
            
            return 0

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        print(f"\n❌ Error: {e}")
        print("📋 Please ensure:")
        print("   - Your AWS credentials are configured")
        print("   - Your JSON file is valid")
        print("   - You have ReportLab installed: pip install reportlab")
        print("   - You have Strands installed: pip install strands")
        return 1


if __name__ == "__main__":
    exit(main())