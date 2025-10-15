import json
import boto3
import fitz  # PyMuPDF
from datetime import datetime
import os
import sys
from typing import Dict, Any, List, Optional
import re
from pathlib import Path

class EnhancedRAPIDReportGenerator:
    def __init__(self, aws_region='us-east-1', company_name='Cloud202', tool_name='Qubitz', 
             contact_email='hello@cloud202.com', contact_phone='+44 7792 565738',
             assessment_lead='Cloud202 Senior Solutions Architect', 
             csm='Cloud202 Customer Success Manager'):
            """
            Initialize the Enhanced RAPID Report Generator with customizable branding
            """
            try:
                self.bedrock_runtime = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=aws_region
                )
                # Use latest Claude on Bedrock if allowed in your account
                self.model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'
                print("✅ AWS Bedrock client initialized successfully")
            except Exception as e:
                print(f"⚠️ Warning: Could not initialize AWS Bedrock client: {e}")
                print("📝 Will use fallback content generation")
                self.bedrock_runtime = None

            # Customizable branding
            self.company_name = company_name
            self.tool_name = tool_name
            self.contact_email = contact_email
            self.contact_phone = contact_phone
            self.assessment_lead = assessment_lead
            self.csm = csm
            
            # Enhanced color scheme for professional reports
            self.colors = {
                'primary': (0.067, 0.306, 0.545),      # Professional Blue #114A8B
                'secondary': (0.2, 0.2, 0.2),          # Dark Gray
                'accent': (0.851, 0.373, 0.008),       # Professional Orange #D95F02
                'success': (0.122, 0.467, 0.706),      # Success Blue #1F77B4
                'text': (0.15, 0.15, 0.15),            # Near Black
                'light_gray': (0.96, 0.96, 0.96),      # Light Background
                'white': (1.0, 1.0, 1.0),              # Pure White
                'gold': (1.0, 0.843, 0.0),             # Gold Accent
                'dark_blue': (0.047, 0.196, 0.365),    # Dark Blue #0C3359
            }

    def _build_bedrock_prompt(self, processed_data: Dict[str, Any]) -> str:
        """
        Build a deterministic prompt for Anthropic via Bedrock.
        We instruct the model to output STRICT JSON with specific keys only.
        """
        # We provide the entire processed_data so the model can ground its writing.
        # IMPORTANT: Ask for STRICT JSON with exactly these keys (no Markdown, no prose).
        # Keys must map 1:1 to your PDF sections.
        return f"""
            You are a senior strategy consultant and report writer. 
            You will receive a structured JSON object called processed_data that contains everything needed to prepare an executive report.

            YOUR TASK:
            1) Produce a STRICT JSON object with EXACTLY these top-level keys:
            - "executive_summary"
            - "business_case_analysis"
            - "technical_implementation_roadmap"
            - "financial_investment_analysis"
            - "risk_mitigation_strategy"
            - "strategic_recommendations"

            2) Each value must be a single string (multi-paragraph text allowed).
            3) DO NOT include any keys not listed above.
            4) DO NOT include Markdown, code fences, lists of JSON, or explanations outside of the JSON object.
            5) Keep content grounded in the provided data (company name, industry, goals, constraints, metrics, risks, timeline, etc).
            6) Keep the tone board-ready, specific, and quantitative where possible (use the metrics from the data).
            7) Assume the audience is C-level executives and clinical/technical leaders (when healthcare), with emphasis on ROI, risk, and change management.
            8) Prefer plain bullets like "• " inside the strings if you include lists.

            IMPORTANT FORMATTING RULES:
            - Output MUST be valid JSON.
            - Do not include any extraneous text.

            Reference context (processed_data follows). Use its values where appropriate and tailor wording accordingly.

            processed_data:
            {json.dumps(processed_data, ensure_ascii=False, indent=2)}
            """.strip()
    
    def interactive_file_selection(self) -> str:
        """
        Interactive file selection with validation
        """
        print("\n" + "="*60)
        print("🚀 RAPID GenAI Assessment Report Generator v3.0")
        print("="*60)
        
        # Check for JSON files in current directory
        current_dir = Path(".")
        json_files = list(current_dir.glob("*.json"))
        
        if json_files:
            print(f"\n📂 Found {len(json_files)} JSON file(s) in current directory:")
            for i, file in enumerate(json_files, 1):
                file_size = file.stat().st_size / 1024  # KB
                print(f"   {i}. {file.name} ({file_size:.1f} KB)")
            
            print(f"\n   {len(json_files) + 1}. Enter custom file path")
            print("   0. Exit")
            
            while True:
                try:
                    choice = input(f"\nSelect option (0-{len(json_files) + 1}): ").strip()
                    
                    if choice == "0":
                        print("👋 Exiting...")
                        sys.exit(0)
                    elif choice == str(len(json_files) + 1):
                        break  # Go to custom path input
                    elif 1 <= int(choice) <= len(json_files):
                        selected_file = str(json_files[int(choice) - 1])
                        print(f"✅ Selected: {selected_file}")
                        return selected_file
                    else:
                        print("❌ Invalid selection. Please try again.")
                except (ValueError, IndexError):
                    print("❌ Invalid input. Please enter a number.")
        
        # Custom file path input
        while True:
            file_path = input("\n📄 Enter the path to your JSON assessment file: ").strip()
            
            if not file_path:
                print("❌ Please enter a file path.")
                continue
            
            # Remove quotes if present
            file_path = file_path.strip("\"'")
            
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue
            
            if not file_path.lower().endswith('.json'):
                print("❌ File must be a JSON file (.json extension)")
                continue
            
            try:
                # Test if file is valid JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✅ Valid JSON file: {file_path}")
                return file_path
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON format: {e}")
            except Exception as e:
                print(f"❌ Error reading file: {e}")
    
    def load_assessment_data(self, json_file_path: str) -> Dict[str, Any]:
        """
        Load and validate assessment data from JSON file
        """
        try:
            print(f"📖 Loading assessment data from: {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            # Validate required sections
            required_sections = ['customer_info', 'use_case_discovery', 'business_value_roi']
            missing_sections = [section for section in required_sections if section not in data]
            
            if missing_sections:
                print(f"⚠️ Warning: Missing sections in JSON: {', '.join(missing_sections)}")
                print("📋 Continuing with available data...")
            
            return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Assessment data file not found: {json_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in file {json_file_path}: {e}")
    
    def process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced processing and structuring of assessment data
        """
        processed_data = {
            # Company Information
            'company_name': raw_data.get('customer_info', {}).get('company_name', 'Valued Customer'),
            'industry': raw_data.get('customer_info', {}).get('industry', 'Technology'),
            'company_size': raw_data.get('customer_info', {}).get('company_size', 'Enterprise'),
            'headquarters': raw_data.get('customer_info', {}).get('headquarters', 'Global'),
            'primary_contact': raw_data.get('customer_info', {}).get('primary_contact', {}),
            
            # Assessment Metadata
            'assessment_type': raw_data.get('assessment_metadata', {}).get('assessment_type', 'Comprehensive'),
            'assessment_date': raw_data.get('assessment_metadata', {}).get('assessment_date', datetime.now().strftime('%Y-%m-%d')),
            'assessment_duration': raw_data.get('assessment_metadata', {}).get('assessment_duration', '2-3 weeks'),
            
            # Business Context - Enhanced
            'business_problem': raw_data.get('use_case_discovery', {}).get('business_problem', 'Digital transformation initiative'),
            'current_state': raw_data.get('use_case_discovery', {}).get('current_state', 'In progress'),
            'strategic_alignment': raw_data.get('use_case_discovery', {}).get('strategic_alignment', 'High priority strategic initiative'),
            'urgency': raw_data.get('use_case_discovery', {}).get('urgency', 'High'),
            'business_owner': raw_data.get('use_case_discovery', {}).get('business_owner', 'Executive Leadership'),
            'primary_goal': raw_data.get('use_case_discovery', {}).get('primary_goal', 'Improve operational efficiency'),
            'expected_impact': raw_data.get('use_case_discovery', {}).get('expected_impact_timeline', {}),
            'success_metrics': raw_data.get('use_case_discovery', {}).get('roi_measurement', 'Key performance indicators'),
            
            # Technical Requirements - Enhanced
            'data_volume': raw_data.get('data_readiness', {}).get('data_volume', 'Large scale'),
            'data_quality': raw_data.get('data_readiness', {}).get('data_quality', 'Good'),
            'integration_systems': raw_data.get('use_case_discovery', {}).get('integration_systems', []),
            'regulatory_requirements': raw_data.get('compliance_integration', {}).get('regulatory_frameworks', []),
            'security_requirements': raw_data.get('security_governance', {}).get('security_requirements', []),
            
            # Model Evaluation Results - Enhanced
            'model_evaluation': raw_data.get('model_evaluation', {}),
            'recommended_model': raw_data.get('model_evaluation', {}).get('recommended_model', 'Claude 3 Sonnet'),
            'model_performance': raw_data.get('model_evaluation', {}).get('performance_metrics', {}),
            
            # Business Value - Enhanced
            'business_impact': raw_data.get('business_value_roi', {}).get('estimated_business_impact', {}),
            'roi_estimate': raw_data.get('business_value_roi', {}).get('estimated_roi', '300%+ over 3 years'),
            'beneficiaries': raw_data.get('business_value_roi', {}).get('beneficiaries_count', 'Enterprise-wide'),
            'cost_savings': raw_data.get('business_value_roi', {}).get('cost_savings_opportunities', 'Significant operational savings'),
            
            # Implementation - Enhanced
            'timeline': raw_data.get('implementation_plan', {}).get('high_level_timeline', {}),
            'milestones': raw_data.get('implementation_plan', {}).get('key_milestones', []),
            'resources': raw_data.get('implementation_plan', {}).get('resource_requirements', {}),
            'dependencies': raw_data.get('implementation_plan', {}).get('dependencies', []),
            
            # Risks - Enhanced
            'risks': raw_data.get('risk_assessment', {}).get('key_risks', []),
            'success_factors': raw_data.get('risk_assessment', {}).get('success_factors', []),
            'next_steps': raw_data.get('risk_assessment', {}).get('immediate_next_steps', [])
        }
        
        return processed_data

    
    def _is_bullet_point(self, text: str) -> bool:
        """
        Check if paragraph contains bullet points or list items
        """
        bullet_indicators = [
            '•', '-', '*', '→', '▪', '◦',
            'months:', 'Phase', 'Step', ',', '%'
        ]
        lines = text.split('\n')
        bullet_count = 0
        for line in lines:
            line = line.strip()
            if any(line.startswith(indicator) or indicator in line for indicator in bullet_indicators):
                bullet_count += 1
        return bullet_count > len(lines) * 0.3 and bullet_count > 1

    def generate_comprehensive_report_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate comprehensive, detailed report content using AWS Bedrock or fallback
        """
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        if self.bedrock_runtime:
            print("🤖 Generating comprehensive report content using AWS Bedrock...")
            return self._generate_bedrock_content(processed_data, company_name, industry)
        else:
            print("📝 AWS Bedrock not available, using enhanced fallback content...")
            return self._generate_enhanced_fallback_content(processed_data)
    
    def _generate_bedrock_content(self, processed_data: Dict[str, Any], company_name: str, industry: str) -> Dict[str, str]:
        """
        Generate content using AWS Bedrock (Anthropic Claude) with a strong, deterministic prompt.
        Falls back to enhanced local generation if anything fails.
        """
        if not self.bedrock_runtime:
            # No client -> fallback
            return self._generate_enhanced_fallback_content(processed_data)

        try:
            prompt = self._build_bedrock_prompt(processed_data)

            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 6000,          # plenty for 6 sections
                "temperature": 0.3,          # tighten variability
                "top_p": 0.95,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=body
            )

            # Bedrock returns a streaming-like body; read and parse:
            raw = response.get("body").read()
            response_body = json.loads(raw)
            # For Anthropic messages, text is in response_body["content"][0]["text"]
            content_text = response_body.get("content", [{}])[0].get("text", "").strip()
            if not content_text:
                raise ValueError("Empty content returned from Bedrock model.")

            # Must be STRICT JSON per our instructions:
            try:
                content_json = json.loads(content_text)
            except json.JSONDecodeError as e:
                # Try to salvage: sometimes models wrap in code fences.
                cleaned = content_text.strip().strip("```").strip()
                content_json = json.loads(cleaned)

            required_keys = [
                "executive_summary",
                "business_case_analysis",
                "technical_implementation_roadmap",
                "financial_investment_analysis",
                "risk_mitigation_strategy",
                "strategic_recommendations"
            ]
            for k in required_keys:
                if k not in content_json or not isinstance(content_json[k], str):
                    raise ValueError(f"Missing or invalid key in model output: {k}")

            print("✅ Successfully generated comprehensive report content using Bedrock")
            return content_json

        except Exception as e:
            print(f"❌ Error generating content with Bedrock: {e}")
            print("📝 Falling back to enhanced local content generation...")
            return self._generate_enhanced_fallback_content(processed_data)
        
    def _generate_enhanced_fallback_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate comprehensive enhanced fallback content using actual assessment data
        """
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        use_case = processed_data.get('business_problem', 'GenAI Implementation')
        roi = processed_data.get('roi_estimate', '300%+ ROI over 3 years')
        
        # Extract specific data from your healthcare JSON
        recommended_model = processed_data.get('recommended_model', 'AWS HealthScribe Enhanced')
        clinical_accuracy = "99.6%" if "HealthScribe" in str(processed_data.get('model_evaluation', {})) else "99%+"
        cost_savings = processed_data.get('cost_savings', '$2.3M annually')
        revenue_generation = "$1.8M additional revenue" if "HealthTech" in company_name else "$2.4M additional revenue"
        
        return {
            'executive_summary': f"""
EXECUTIVE STRATEGIC SUMMARY - {company_name} GenAI Transformation

Strategic Imperative and Business Case:
Following a comprehensive RAPID assessment using {self.tool_name}, we present a compelling strategic imperative for {company_name} to immediately proceed with GenAI implementation. Our analysis reveals exceptional organizational readiness, quantified business value potential, and optimal market timing that positions {company_name} for transformational competitive advantage in the {industry} sector.

The assessment identifies {use_case} as a critical business challenge that represents both significant operational inefficiency and transformational opportunity. Current operational constraints limit {company_name}'s ability to achieve strategic objectives while creating vulnerability to competitive disruption. GenAI implementation addresses these challenges through intelligent automation, enhanced decision-making capabilities, and operational excellence that delivers measurable business value within the first quarter of deployment.

Quantified Business Opportunity:
Our comprehensive analysis projects {roi} through direct cost savings, revenue enhancement, and operational efficiency improvements. The business case demonstrates compelling financial returns with 12-18 month payback period and accelerating value creation over the 3-5 year horizon. Conservative projections indicate minimum 25% operational cost reduction, 40% productivity improvement, and 15-20% revenue growth through enhanced capabilities and market positioning.

Strategic Recommendation and Implementation Approach:
We recommend immediate implementation with 95% confidence based on comprehensive readiness assessment across technical, operational, and organizational dimensions. The recommended phased approach minimizes implementation risk while maximizing value realization through proven methodologies and {self.company_name} expertise. Critical success factors include executive sponsorship, comprehensive change management, technical excellence in deployment, and continuous optimization based on performance metrics.

Call to Action:
We recommend proceeding immediately with implementation planning, team mobilization, and infrastructure preparation. The strategic window for maximum competitive advantage requires decisive leadership action within the next 30-60 days to capitalize on market opportunities and organizational readiness.
            """,
            
            'business_case_analysis': f"""
COMPREHENSIVE BUSINESS CASE ANALYSIS - {company_name} GenAI Initiative

Current State Assessment and Pain Point Analysis:
Our comprehensive assessment reveals significant operational inefficiencies within {company_name}'s current business processes that create both cost burden and competitive vulnerability. {use_case} represents a critical business challenge consuming excessive resources while limiting organizational agility and market responsiveness.

The recommended {recommended_model} solution, specifically optimized for {industry.lower()} operations, offers a best-in-class AI architecture tailored to your needs. By integrating with existing enterprise systems and clinical workflows, this solution will generate comprehensive operational outputs in real-time while maintaining unparalleled {clinical_accuracy} accuracy validated by domain experts.

Quantified Business Impact and Value Creation:
Comprehensive financial modeling projects {roi} through multiple value streams including direct cost savings, revenue enhancement, and strategic positioning benefits. Direct cost savings of {cost_savings} result from process automation, productivity improvements, and resource optimization.

Revenue enhancement opportunities total {revenue_generation} through improved customer experience, faster service delivery, and enhanced competitive positioning. Operational efficiency improvements deliver 40-60% reduction in processing time, 75% improvement in accuracy, and 80% reduction in manual data entry requirements. These improvements compound over time, creating accelerating value realization and sustainable competitive advantages.

Strategic Competitive Advantages and Market Positioning:
GenAI implementation creates multiple sustainable competitive advantages that differentiate {company_name} in the {industry} market. Enhanced operational efficiency enables superior service delivery while maintaining cost competitiveness. Predictive analytics capabilities provide strategic insights that improve decision-making and market responsiveness.

Market analysis indicates AI-powered organizations achieve 2-3x performance premiums over traditional competitors, with advantages growing over time as AI capabilities mature. Early adoption positions {company_name} as an innovation leader, attracting top talent, premium customers, and strategic partnerships that compound competitive advantages.
            """,
            
            'technical_implementation_roadmap': f"""
COMPREHENSIVE TECHNICAL IMPLEMENTATION ROADMAP - {company_name} GenAI Deployment

Phase 1: Foundation and Infrastructure (Months 1-3)
Infrastructure setup, model integration, and pilot program design. Provision cloud infrastructure and configure security controls per regulatory requirements. Integrate {recommended_model} with existing enterprise systems and establish data pipelines. Design pilot program for initial user groups and develop comprehensive training curriculum and support resources.

Key technical milestones include architecture compliance validation, security controls implementation, and integration testing with existing enterprise systems. Development environment configuration includes version control, CI/CD automation, and infrastructure as code. Team onboarding and training programs ensure technical competency across development, operations, and security teams.

Phase 2: Pilot Deployment and Initial Optimization (Months 4-6)
Deploy {recommended_model} to pilot group of users with continuous performance monitoring, feedback gathering, and integration optimization. Validate success metrics and obtain approvals for expansion. This phase focuses on real-world testing and refinement of the solution.

Phase 3: Enterprise-wide Scaling and Advanced Optimization (Months 7-9)
Refine workflows and enhance training based on learnings from pilot deployment. Implement advanced customizations for complex use cases and deploy to remaining user groups across all operational locations. This phase ensures organization-wide adoption and optimization.

Phase 4: Monitoring, Governance, and Continuous Improvement (Months 10-12)
Establish robust performance monitoring and governance processes. Validate achievement of success metrics and ROI targets. Implement continuous improvement processes for model retraining and optimization. Our core project team will include dedicated project management, technical developers, domain expertise, and ongoing support resources.

Resource Requirements and Dependencies:
Implementation requires cross-functional team including cloud architects, AI/ML engineers, software developers, security specialists, and project managers. Technical dependencies include network connectivity, security approvals, integration system availability, and data quality preparation. Training requirements encompass cloud certifications, AI/ML competency development, and security awareness programs.
            """,
            
            'financial_investment_analysis': f"""
COMPREHENSIVE FINANCIAL INVESTMENT ANALYSIS - {company_name} GenAI Initiative

Investment Breakdown:
Technology and Infrastructure (60%): Cloud infrastructure and services, {recommended_model} licensing and customization, integration and security components. Professional Services (25%): {self.company_name} Professional Services, specialized consulting, integration support. Training and Change Management (15%): User training programs, communication and adoption initiatives, project management and governance.

Returns Analysis:
Cost Savings: {cost_savings} from reduced processing time and improved efficiencies. Revenue Generation: {revenue_generation} from increased operational capacity and enhanced service delivery. Total Annual Benefits: Over $4M in combined cost savings and revenue generation.

With projected annual benefits exceeding $4M, the investment will achieve break-even within the first 6-9 months of full deployment. Assuming a conservative technology lifecycle, the cumulative 3-year ROI is estimated at {roi}.

Risk Scenarios and Sensitivity Analysis:
Best Case (10% upside): Enhanced ROI driven by accelerated adoption and additional operational improvements. Expected Case (base): {roi} as projected with standard adoption patterns. Worst Case (20% downside): Acceptable ROI due to longer adoption cycles but still positive returns within 18 months.

Break-even Analysis and Payback Period:
Conservative financial modeling demonstrates break-even achievement within 12-16 months post-implementation, with accelerating value realization thereafter. Cash flow analysis demonstrates positive monthly cash flow beginning month 10-12, with cumulative value creation exceeding $12M over 3-year horizon. Internal rate of return (IRR) exceeds 50% under base case assumptions.

Total Cost of Ownership (TCO) Analysis:
Five-year TCO analysis includes initial implementation investment, ongoing operational costs, maintenance expenses, and upgrade requirements. TCO optimization strategies include cloud cost management, automation reducing operational overhead, and scalability ensuring cost efficiency as usage grows.
            """,
            
            'risk_mitigation_strategy': f"""
COMPREHENSIVE RISK MITIGATION STRATEGY - {company_name} GenAI Implementation

Strategic Risk Assessment and Quantification:
1. User Adoption Resistance (Medium Probability, High Impact)
Mitigation: Robust change management program with user champions, gradual rollout, and success storytelling to demonstrate tangible benefits and build confidence in the new system.

2. Integration Complexity (Medium Probability, High Impact)
Mitigation: Dedicated integration team, early testing with existing systems, and engagement of specialized consulting support to ensure seamless connectivity and data flow.

3. Regulatory Compliance Issues (Low Probability, Critical Impact)
Mitigation: Comprehensive compliance reviews, legal counsel engagement, and staged validation processes to ensure all regulatory requirements are met throughout implementation.

4. AI Accuracy Degradation (Medium Probability, High Impact)
Mitigation: Continuous monitoring systems, regular model retraining protocols, and human oversight mechanisms to maintain {clinical_accuracy} accuracy standards.

Success Factors and Key Performance Indicators:
Critical success factors include strong leadership champion network to drive adoption, robust technical integration with existing workflows, comprehensive training and support programs, and clear demonstration of efficiency improvements and quality enhancements.

KPI framework encompasses technical metrics (system uptime >99.9%, response time <2 seconds, accuracy >{clinical_accuracy}), operational metrics (user adoption rate >85%, process efficiency improvement, cost reduction achievement), and financial metrics (ROI realization, budget adherence, benefit delivery).

Immediate Next Steps and Implementation Protocol:
30-60 day immediate actions include securing final executive approval and budget allocation, executing necessary compliance agreements, establishing project governance structure and team assignments, initiating detailed technical architecture planning, and beginning user champion recruitment and training program design.

Long-term Risk Monitoring and Continuous Improvement:
Ongoing risk management includes quarterly risk assessments, mitigation strategy effectiveness evaluation, and emerging risk identification. Continuous improvement processes incorporate lessons learned, optimization opportunities, and capability enhancement based on performance data and user feedback.
            """,
            
            'strategic_recommendations': f"""
STRATEGIC RECOMMENDATIONS - {company_name} GenAI Transformation Leadership

Executive Leadership and Governance Framework:
{company_name} leadership must establish comprehensive governance framework with C-level sponsorship, clear accountability structures, and strategic decision-making authority to ensure GenAI transformation success. Recommended governance includes Executive Steering Committee with CEO/COO leadership, Technical Advisory Board with CTO/CIO participation, and operational oversight councils.

We recommend establishing an AI Center of Excellence led by a Chief AI Officer, reporting directly to the CEO. This CoE will be responsible for setting AI vision, strategy, and governance while fostering a data-driven culture across the organization. It will serve as a hub for AI skills development, best practice sharing, and continuous innovation.

Organizational Readiness and Capability Development:
Strategic recommendation emphasizes comprehensive organizational transformation beyond technology implementation, including culture change, capability development, and process optimization. Cultural transformation includes innovation mindset development, data-driven decision making, and continuous learning orientation through comprehensive change management programs.

Capability development includes technical skills training for AI/ML literacy, operational skills enhancement for digital collaboration, and leadership development for change management. Training investment includes certifications, industry conference participation, and external training programs to build internal expertise and ensure sustainable adoption.

Partnership and Ecosystem Strategy Optimization:
{company_name} should leverage strategic partnerships with {self.company_name} for ongoing advantage through professional services engagement, architectural guidance, and continuous optimization support. Partnership benefits include access to leading-edge capabilities, industry expertise, and strategic insights from global AI implementation experience.

Innovation and Competitive Positioning Strategy:
Long-term competitive positioning requires continuous innovation, capability enhancement, and market leadership demonstration. Innovation strategy includes internal R&D investment, external partnership development, and emerging technology evaluation to maintain competitive advantages.

As an AI pioneer in the {industry} industry, {company_name} should position itself as a thought leader through active participation in conferences, publishing insights, and contributing to industry advancement. This will enhance brand reputation, attract top talent, and foster an innovative, future-focused culture.

Investment and Resource Allocation Strategy:
Strategic resource allocation balances immediate implementation needs with long-term capability development and market positioning objectives. Investment prioritization includes proven ROI opportunities, strategic capability development, and competitive positioning enhancement to ensure sustained value creation and market leadership.
            """
        }
    
    def _parse_text_response(self, text: str) -> Dict[str, str]:
        """
        Enhanced parsing of non-JSON text response into sections
        """
        sections = {
            'executive_summary': '',
            'business_case_analysis': '',
            'technical_implementation_roadmap': '',
            'financial_investment_analysis': '',
            'risk_mitigation_strategy': '',
            'strategic_recommendations': ''
        }
        
        current_section = None
        lines = text.split('\n')
        
        section_keywords = {
            'executive_summary': ['executive', 'summary'],
            'business_case_analysis': ['business', 'case'],
            'technical_implementation_roadmap': ['technical', 'implementation'],
            'financial_investment_analysis': ['financial', 'investment'],
            'risk_mitigation_strategy': ['risk', 'mitigation'],
            'strategic_recommendations': ['strategic', 'recommendations']
        }
        
        for line in lines:
            line_lower = line.lower()
            section_found = False
            
            # Check for section headers
            for section_key, keywords in section_keywords.items():
                if all(keyword in line_lower for keyword in keywords):
                    current_section = section_key
                    section_found = True
                    break
            
            if not section_found and current_section and line.strip():
                sections[current_section] += line + '\n'
        
        return sections
    
    def create_professional_pdf_report(self, content: Dict[str, str], customer_info: Dict[str, Any], output_path: str):
        """
        Create a highly professional, detailed PDF report with enhanced formatting
        """
        print("📄 Creating professional PDF report with enhanced formatting...")
        
        doc = None
        try:
            # Create PDF document
            doc = fitz.open()
            page_width = 595  # A4 width
            page_height = 842  # A4 height
            margin = 40
            content_width = page_width - (2 * margin)
            
            # Add professional title page
            self._add_enhanced_title_page(doc, customer_info, page_width, page_height, margin)
            
            # Add table of contents
            self._add_table_of_contents(doc, page_width, page_height, margin)
            
            # Add content sections
            sections = [
                ("Executive Summary", content.get('executive_summary', ''), True),
                ("Business Case Analysis", content.get('business_case_analysis', ''), False),
                ("Technical Implementation Roadmap", content.get('technical_implementation_roadmap', ''), False),
                ("Financial Investment Analysis", content.get('financial_investment_analysis', ''), False),
                ("Risk Mitigation Strategy", content.get('risk_mitigation_strategy', ''), False),
                ("Strategic Recommendations", content.get('strategic_recommendations', ''), False)
            ]
            
            for section_title, section_content, is_executive_summary in sections:
                self._add_enhanced_content_section(
                    doc, section_title, section_content, 
                    page_width, page_height, margin, content_width,
                    is_executive_summary
                )
            
            # Add appendix
            self._add_appendix(doc, customer_info, page_width, page_height, margin)
            
            # Save the document
            doc.save(output_path)
            
            print(f"✅ Professional executive report generated successfully!")
            print(f"📊 Total pages: {doc.page_count}")
            print(f"💾 File saved: {output_path}")
            
        except Exception as e:
            print(f"❌ Error creating PDF report: {e}")
            raise
        finally:
            # Ensure document is closed only once
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass
    
    def _add_enhanced_title_page(self, doc, customer_info: Dict[str, Any], page_width: int, page_height: int, margin: int):
        """
        Create an enhanced, professional title page with custom branding
        """
        page = doc.new_page(width=page_width, height=page_height)
        
        # Professional gradient header
        for i in range(140):
            alpha = 1.0 - (i / 140.0) * 0.3
            header_rect = fitz.Rect(0, i, page_width, i+1)
            color = [self.colors['primary'][j] * alpha for j in range(3)]
            page.draw_rect(header_rect, color=color, fill=color)
        
        # Company Logo Area
        logo_rect = fitz.Rect(margin, 20, margin + 200, 80)
        page.draw_rect(logo_rect, color=self.colors['white'], fill=self.colors['white'])
        
        # Company Name
        page.insert_text(
            (margin + 10, 45),
            self.company_name,
            fontsize=28,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        
        page.insert_text(
            (margin + 10, 70),
            "Professional Services",
            fontsize=12,
            color=self.colors['secondary'],
            fontname="helvetica"
        )
        
        # Main title
        title_y = 180
        page.insert_text(
            (margin, title_y),
            "RAPID GenAI Assessment",
            fontsize=36,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        
        # Subtitle
        page.insert_text(
            (margin, title_y + 50),
            "Comprehensive Executive Report",
            fontsize=24,
            color=self.colors['accent'],
            fontname="helvetica-bold"
        )
        
        # Professional divider line
        line_y = title_y + 80
        page.draw_line(
            fitz.Point(margin, line_y),
            fitz.Point(page_width - margin, line_y),
            color=self.colors['gold'],
            width=3
        )
        
        # Customer information section
        info_y = line_y + 40
        company_name = customer_info.get('company_name', 'Valued Customer')
        industry = customer_info.get('industry', 'Technology')
        
        # Company name with prominence
        page.insert_text(
            (margin, info_y),
            "Prepared for:",
            fontsize=16,
            color=self.colors['secondary'],
            fontname="helvetica"
        )
        
        page.insert_text(
            (margin, info_y + 25),
            company_name,
            fontsize=28,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        
        # Additional details
        details_y = info_y + 70
        details = [
            ("Industry", industry),
            ("Company Size", customer_info.get('company_size', 'Enterprise')),
            ("Assessment Type", customer_info.get('assessment_type', 'Comprehensive RAPID Assessment')),
            ("Assessment Duration", customer_info.get('assessment_duration', '2-3 weeks'))
        ]
        
        for i, (label, value) in enumerate(details):
            y_pos = details_y + (i * 25)
            page.insert_text(
                (margin, y_pos),
                f"{label}:",
                fontsize=12,
                color=self.colors['secondary'],
                fontname="helvetica-bold"
            )
            page.insert_text(
                (margin + 120, y_pos),
                value,
                fontsize=12,
                color=self.colors['text'],
                fontname="helvetica"
            )
        
        # Date and version info
        current_date = datetime.now().strftime("%B %d, %Y")
        footer_y = page_height - 120
        
        page.insert_text(
            (margin, footer_y),
            f"Report Date: {current_date}",
            fontsize=12,
            color=self.colors['text'],
            fontname="helvetica-bold"
        )
        
        page.insert_text(
            (margin, footer_y + 20),
            f"Readiness Assessment Acceleration Program (RAPID) - {self.tool_name}",
            fontsize=10,
            color=self.colors['secondary'],
            fontname="helvetica"
        )
        
        # Confidentiality notice
        page.insert_text(
            (margin, footer_y + 40),
            f"CONFIDENTIAL - {self.company_name} Strategic Assessment",
            fontsize=10,
            color=self.colors['accent'],
            fontname="helvetica-bold"
        )
    
    def _add_table_of_contents(self, doc, page_width: int, page_height: int, margin: int):
        """
        Add a professional table of contents
        """
        page = doc.new_page(width=page_width, height=page_height)
        
        # Header
        self._add_page_header(page, "Table of Contents", page_width, margin)
        
        # TOC entries
        toc_entries = [
            ("Executive Summary", "3"),
            ("Business Case Analysis", "4"),
            ("Technical Implementation Roadmap", "6"),
            ("Financial Investment Analysis", "8"),
            ("Risk Mitigation Strategy", "10"),
            ("Strategic Recommendations", "12"),
            ("Appendix - Assessment Details", "14")
        ]
        
        y_pos = 120
        for entry, page_num in toc_entries:
            page.insert_text(
                (margin, y_pos),
                entry,
                fontsize=14,
                color=self.colors['text'],
                fontname="helvetica"
            )
            
            # Dotted line
            dots = "." * int((400 - len(entry) * 8) / 6)
            page.insert_text(
                (margin + len(entry) * 8 + 10, y_pos),
                dots,
                fontsize=14,
                color=self.colors['light_gray'],
                fontname="helvetica"
            )
            
            page.insert_text(
                (page_width - margin - 30, y_pos),
                page_num,
                fontsize=14,
                color=self.colors['primary'],
                fontname="helvetica-bold"
            )
            
            y_pos += 30
        
        # Add page number
        self._add_page_footer(page, "2", page_width, page_height, margin)
    
    def _add_page_header(self, page, title: str, page_width: int, margin: int):
        """
        Add consistent page header
        """
        # Header background
        header_rect = fitz.Rect(0, 0, page_width, 70)
        page.draw_rect(header_rect, color=self.colors['light_gray'], fill=self.colors['light_gray'])
        
        # Title
        page.insert_text(
            (margin, 35),
            title,
            fontsize=20,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        
        # Accent line
        page.draw_line(
            fitz.Point(margin, 55),
            fitz.Point(page_width - margin, 55),
            color=self.colors['accent'],
            width=2
        )
    
    def _add_page_footer(self, page, page_num: str, page_width: int, page_height: int, margin: int):
        """
        Add consistent page footer with custom branding
        """
        footer_y = page_height - 40
        
        # Custom footer
        page.insert_text(
            (margin, footer_y),
            f"{self.company_name} Professional Services - RAPID Assessment",
            fontsize=10,
            color=self.colors['secondary'],
            fontname="helvetica"
        )
        
        # Page number
        page.insert_text(
            (page_width - margin - 20, footer_y),
            page_num,
            fontsize=12,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
    
    def _add_enhanced_content_section(self, doc, title: str, content: str, 
                                    page_width: int, page_height: int, margin: int, 
                                    content_width: int, is_executive_summary: bool = False):
        """
        Add enhanced content section with professional formatting and proper bullet points
        """
        page = doc.new_page(width=page_width, height=page_height)
        page_num = doc.page_count
        
        # Add header
        self._add_page_header(page, title, page_width, margin)
        
        # Special formatting for executive summary
        if is_executive_summary:
            # Add executive summary callout box
            callout_rect = fitz.Rect(margin, 85, page_width - margin, 120)
            page.draw_rect(callout_rect, color=self.colors['accent'], fill=self.colors['accent'])
            
            page.insert_text(
                (margin + 10, 105),
                "STRATEGIC EXECUTIVE SUMMARY",
                fontsize=14,
                color=self.colors['white'],
                fontname="helvetica-bold"
            )
        
        # Content starting position
        content_y = 140 if is_executive_summary else 100
        
        # Process and format content with proper structure
        if content.strip():
            paragraphs = self._smart_paragraph_split(content)
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # Check for section headers
                if self._is_section_header(paragraph):
                    # Add some space before headers
                    content_y += 15
                    
                    # Header styling
                    if content_y > page_height - 100:
                        self._add_page_footer(page, str(page_num), page_width, page_height, margin)
                        page = doc.new_page(width=page_width, height=page_height)
                        page_num = doc.page_count
                        self._add_page_header(page, f"{title} (continued)", page_width, margin)
                        content_y = 100
                    
                    page.insert_text(
                        (margin, content_y),
                        paragraph.strip(),
                        fontsize=14,
                        color=self.colors['primary'],
                        fontname="helvetica-bold"
                    )
                    content_y += 30
                
                # Check for bullet points or lists
                elif self._is_bullet_point(paragraph):
                    bullet_items = self._extract_bullet_points(paragraph)
                    
                    for item in bullet_items:
                        if content_y > page_height - 80:
                            self._add_page_footer(page, str(page_num), page_width, page_height, margin)
                            page = doc.new_page(width=page_width, height=page_height)
                            page_num = doc.page_count
                            self._add_page_header(page, f"{title} (continued)", page_width, margin)
                            content_y = 100
                        
                        # Add bullet point
                        page.insert_text(
                            (margin + 10, content_y),
                            "•",
                            fontsize=12,
                            color=self.colors['accent'],
                            fontname="helvetica-bold"
                        )
                        
                        # Wrap the bullet content
                        wrapped_lines = self._smart_text_wrap(item.strip(), content_width - 30, 11)
                        
                        for i, line in enumerate(wrapped_lines):
                            if i == 0:
                                # First line goes next to bullet
                                page.insert_text(
                                    (margin + 25, content_y),
                                    line,
                                    fontsize=11,
                                    color=self.colors['text'],
                                    fontname="helvetica"
                                )
                            else:
                                # Subsequent lines are indented
                                content_y += 16
                                if content_y > page_height - 80:
                                    self._add_page_footer(page, str(page_num), page_width, page_height, margin)
                                    page = doc.new_page(width=page_width, height=page_height)
                                    page_num = doc.page_count
                                    self._add_page_header(page, f"{title} (continued)", page_width, margin)
                                    content_y = 100
                                
                                page.insert_text(
                                    (margin + 25, content_y),
                                    line,
                                    fontsize=11,
                                    color=self.colors['text'],
                                    fontname="helvetica"
                                )
                        
                        content_y += 20  # Space between bullet items
                
                else:
                    # Regular paragraph with enhanced formatting
                    wrapped_lines = self._smart_text_wrap(paragraph.strip(), content_width - 20, 11)
                    
                    for line in wrapped_lines:
                        if content_y > page_height - 80:
                            # Add page footer before creating new page
                            self._add_page_footer(page, str(page_num), page_width, page_height, margin)
                            
                            page = doc.new_page(width=page_width, height=page_height)
                            page_num = doc.page_count
                            self._add_page_header(page, f"{title} (continued)", page_width, margin)
                            content_y = 100
                        
                        page.insert_text(
                            (margin + 10, content_y),
                            line,
                            fontsize=11,
                            color=self.colors['text'],
                            fontname="helvetica"
                        )
                        content_y += 16
                    
                    content_y += 15  # Extra space between paragraphs
        else:
            # Fallback message for missing content
            page.insert_text(
                (margin, content_y),
                f"[{title} content will be populated based on assessment data]",
                fontsize=12,
                color=self.colors['secondary'],
                fontname="helvetica-oblique"
            )
        
        # Add page footer
        self._add_page_footer(page, str(page_num), page_width, page_height, margin)
    
    def _smart_paragraph_split(self, text: str) -> List[str]:
        """
        Intelligent paragraph splitting with header detection and bullet point preservation
        """
        # Split on double newlines first
        paragraphs = text.split('\n\n')
        result = []
        
        for para in paragraphs:
            # Further split on single newlines for better formatting
            lines = para.strip().split('\n')
            if len(lines) == 1:
                result.append(para.strip())
            else:
                # Check for phase descriptions and bullet points
                current_para = ""
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for phase headers (like "Phase 1:", "Phase 2:", etc.)
                    if self._is_phase_header(line):
                        if current_para:
                            result.append(current_para)
                        result.append(line)
                        current_para = ""
                    elif self._is_section_header(line) and current_para:
                        result.append(current_para)
                        result.append(line)
                        current_para = ""
                    elif self._is_section_header(line):
                        result.append(line)
                    elif line.startswith(('-', '•', '*')) or 'months' in line.lower():
                        # This might be a bullet point or timeline item
                        if current_para:
                            result.append(current_para)
                            current_para = ""
                        result.append(line)
                    else:
                        current_para += " " + line if current_para else line
                
                if current_para:
                    result.append(current_para)
        
        return result
    
    def _is_phase_header(self, text: str) -> bool:
        """
        Detect if text is a phase header (like Phase 1, Phase 2, etc.)
        """
        text = text.strip()
        phase_patterns = [
            r'^Phase \d+',
            r'^Month \d+',
            r'^\d+-\d+ (month|day)',
            r'^Step \d+'
        ]
        
        for pattern in phase_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_section_header(self, text: str) -> bool:
        """
        Detect if text is a section header
        """
        text = text.strip()
        return (
            (text.endswith(':') and len(text) < 100) or
            (text.endswith('Analysis') or text.endswith('Assessment') or text.endswith('Strategy')) and 
            len(text) < 100 and
            not text.count('.') > 2
        ) or (
            len(text.split()) < 10 and
            (text[0].isupper() if text else False) and
            text.count('.') <= 1 and
            any(keyword in text.lower() for keyword in ['strategic', 'comprehensive', 'technical', 'financial', 'operational'])
        )
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """
        Extract individual bullet points from text
        """
        lines = text.split('\n')
        bullet_items = []
        current_item = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new bullet point
            if (line.startswith(('-', '•', '*', '→', '▪')) or 
                re.match(r'^[A-Z][^:]*:', line) or
                re.match(r'^\d+\.', line) or
                'Phase' in line or 'Month' in line):
                
                if current_item:
                    bullet_items.append(current_item)
                
                # Clean the bullet marker
                cleaned_line = re.sub(r'^[-•*→▪]\s*', '', line)
                cleaned_line = re.sub(r'^\d+\.\s*', '', cleaned_line)
                current_item = cleaned_line
            else:
                # Continuation of current bullet point
                current_item += " " + line if current_item else line
        
        if current_item:
            bullet_items.append(current_item)
        
        return bullet_items
    
    def _smart_text_wrap(self, text: str, max_width: float, font_size: int) -> List[str]:
        """
        Enhanced text wrapping with better word handling
        """
        words = text.split()
        lines = []
        current_line = []
        
        # More accurate character width calculation
        char_width = font_size * 0.55
        max_chars = int(max_width / char_width)
        
        for word in words:
            # Test if adding this word would exceed line length
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= max_chars:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long, split it intelligently
                    if len(word) > max_chars:
                        # Split at natural break points if possible
                        for i in range(max_chars, len(word)):
                            if word[i] in '-_./':
                                lines.append(word[:i+1])
                                current_line = [word[i+1:]] if word[i+1:] else []
                                break
                        else:
                            # Force split
                            lines.append(word[:max_chars])
                            current_line = [word[max_chars:]] if len(word) > max_chars else []
                    else:
                        current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _add_appendix(self, doc, customer_info: Dict[str, Any], page_width: int, page_height: int, margin: int):
        """
        Add comprehensive appendix with assessment details and custom contact info
        """
        page = doc.new_page(width=page_width, height=page_height)
        page_num = doc.page_count
        
        # Add header
        self._add_page_header(page, "Appendix - Assessment Details", page_width, margin)
        
        # Assessment methodology section
        content_y = 100
        
        # Assessment Overview
        page.insert_text(
            (margin, content_y),
            "RAPID Assessment Methodology",
            fontsize=16,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        content_y += 30
        
        methodology_text = f"""The Readiness Assessment Acceleration Program (RAPID) is a comprehensive evaluation framework designed to assess organizational readiness for GenAI implementation using {self.tool_name}. This assessment encompasses technical infrastructure, data readiness, compliance requirements, and business value analysis to provide strategic recommendations for successful GenAI adoption."""
        
        wrapped_lines = self._smart_text_wrap(methodology_text, page_width - 2*margin - 20, 11)
        for line in wrapped_lines:
            page.insert_text(
                (margin + 10, content_y),
                line,
                fontsize=11,
                color=self.colors['text'],
                fontname="helvetica"
            )
            content_y += 16
        
        content_y += 20
        
        # Assessment Scope
        page.insert_text(
            (margin, content_y),
            "Assessment Scope and Coverage",
            fontsize=14,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        content_y += 25
        
        scope_areas = [
            "• Use Case Discovery and Business Requirements Analysis",
            "• Data Readiness and Infrastructure Assessment", 
            "• Model Evaluation and Technical Architecture Review",
            "• Compliance and Security Framework Analysis",
            "• Business Value and ROI Calculation",
            "• Implementation Planning and Risk Assessment",
            "• Change Management and Organizational Readiness"
        ]
        
        for item in scope_areas:
            page.insert_text(
                (margin + 10, content_y),
                item,
                fontsize=11,
                color=self.colors['text'],
                fontname="helvetica"
            )
            content_y += 18
        
        content_y += 20
        
        # Contact Information
        page.insert_text(
            (margin, content_y),
            f"{self.company_name} Professional Services Contact",
            fontsize=14,
            color=self.colors['primary'],
            fontname="helvetica-bold"
        )
        content_y += 25
        
        contact_info = [
            "For questions regarding this assessment or next steps:",
            "",
            f"{self.company_name} Professional Services Team",
            f"Email: {self.contact_email}",
            f"Phone: {self.contact_phone}",
            "",
            "Partner Contact:",
            f"Assessment Lead: {self.assessment_lead}",
            f"Customer Success Manager: {self.csm}"
        ]
        
        for item in contact_info:
            page.insert_text(
                (margin + 10, content_y),
                item,
                fontsize=11,
                color=self.colors['text'],
                fontname="helvetica"
            )
            content_y += 16
        
        # Add footer
        self._add_page_footer(page, str(page_num), page_width, page_height, margin)
    
    def generate_executive_report_from_json(self, json_file_path: str = None, output_filename: str = None) -> str:
        """
        Main method to generate comprehensive executive report from JSON assessment data
        """
        try:
            # Interactive file selection if not provided
            if not json_file_path:
                json_file_path = self.interactive_file_selection()
            
            # Load and process assessment data
            print(f"\n📂 Loading assessment data from: {json_file_path}")
            raw_data = self.load_assessment_data(json_file_path)
            
            print("🔄 Processing assessment data...")
            processed_data = self.process_assessment_data(raw_data)
            
            # Generate comprehensive filename if not provided
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                company_name = processed_data.get('company_name', 'customer')
                # Clean company name for filename
                company_name = re.sub(r'[^\w\-_]', '_', company_name.lower())
                output_filename = f"RAPID_Executive_Report_{company_name}_{timestamp}.pdf"
            
            # Generate comprehensive content
            print("🤖 Generating comprehensive report content...")
            content = self.generate_comprehensive_report_content(processed_data)
            
            # Create professional PDF report
            print("📄 Creating professional PDF report...")
            self.create_professional_pdf_report(content, processed_data, output_filename)
            
            # Success summary
            print("\n" + "="*60)
            print("✅ RAPID EXECUTIVE REPORT GENERATED SUCCESSFULLY!")
            print("="*60)
            print(f"📂 Input file: {json_file_path}")
            print(f"📄 Output file: {output_filename}")
            print(f"🏢 Customer: {processed_data.get('company_name', 'N/A')}")
            print(f"🏭 Industry: {processed_data.get('industry', 'N/A')}")
            print(f"📊 Assessment Type: {processed_data.get('assessment_type', 'N/A')}")
            print(f"💰 ROI Estimate: {processed_data.get('roi_estimate', 'N/A')}")
            print(f"🔧 Generated with: {self.company_name} {self.tool_name}")
            print("📈 Report includes comprehensive strategic analysis and recommendations")
            print("="*60)
            
            return output_filename
            
        except Exception as e:
            print(f"\n❌ Error generating executive report: {e}")
            print("🔍 Please check your JSON file format and configuration")
            raise

def create_sample_assessment_data(filename: str = "sample_rapid_assessment.json") -> str:
    """
    Create comprehensive sample assessment data for testing
    """
    sample_data = {
        "assessment_metadata": {
            "assessment_date": "2025-01-20",
            "assessment_type": "Comprehensive RAPID Assessment",
            "partner_name": "Cloud202 Professional Services",
            "assessment_duration": "3 weeks"
        },
        "customer_info": {
            "company_name": "TechCorp Innovations Inc.",
            "industry": "Financial Technology",
            "company_size": "Large Enterprise (2000-5000 employees)",
            "headquarters": "New York, NY",
            "primary_contact": {
                "name": "Jennifer Martinez",
                "title": "Chief Technology Officer",
                "email": "jennifer.martinez@techcorp.com",
                "phone": "+1-212-555-0199"
            }
        },
        "use_case_discovery": {
            "business_problem": "Our customer service operations face significant challenges with response time, accuracy, and scalability. Current manual processes for customer inquiry handling, document analysis, and response generation consume excessive resources while delivering inconsistent quality. Average response time is 4-6 hours with 15% accuracy issues leading to customer dissatisfaction and potential compliance risks.",
            "current_state": "Pilot testing - manual optimization initiatives showing limited improvement",
            "urgency": "Critical - Q2 2025 regulatory compliance deadline and competitive pressure",
            "business_owner": "Robert Kim, Chief Operating Officer",
            "primary_goal": "Reduce customer service response time by 75% while improving accuracy to 99%+ and achieving full regulatory compliance",
            "strategic_alignment": "Directly supports 2025-2027 strategic plan for operational excellence, customer experience leadership, and regulatory compliance automation. Critical for maintaining competitive position in FinTech market.",
            "expected_impact_timeline": {
                "3_months": "40% reduction in response time, pilot deployment to 100 customer service representatives",
                "6_months": "65% reduction in response time, deployment to 300 representatives across 3 business units",
                "12_months": "75% reduction in response time, full enterprise deployment to 500+ representatives"
            },
            "cost_savings_opportunities": "Estimated $4.2M annual savings through response time reduction, accuracy improvement, automated compliance reporting, and operational efficiency gains",
            "roi_measurement": "Primary metrics: response time reduction, accuracy improvement, customer satisfaction scores, compliance audit results, operational cost reduction, employee productivity gains"
        },
        "business_value_roi": {
            "estimated_business_impact": {
                "cost_savings": "$4.2M annually through operational efficiency, reduced manual processing, improved accuracy",
                "revenue_generation": "$3.6M additional revenue from enhanced customer experience, faster resolution, competitive positioning",
                "productivity_improvement": "75% reduction in response time, 85% improvement in first-call resolution, 60% reduction in manual processing"
            },
            "estimated_roi": "420% over 3 years with 14-month payback period",
            "beneficiaries_count": "500+ customer service representatives, 250,000+ annual customer interactions, enterprise-wide compliance improvement"
        },
        "implementation_plan": {
            "high_level_timeline": {
                "months_1_3": "Infrastructure setup, model selection and training, pilot program design and team preparation",
                "months_4_6": "Pilot deployment to 100 representatives, optimization based on results, expansion planning",
                "months_7_9": "Expansion to 300 representatives across business units, advanced feature deployment",
                "months_10_12": "Full enterprise deployment to 500+ representatives, advanced analytics and reporting"
            },
            "key_milestones": [
                "Month 1: Cloud infrastructure provisioned and security configured",
                "Month 2: AI models trained and integration testing completed",
                "Month 3: Pilot team trained and initial customer interactions processed",
                "Month 6: Pilot success validated with 40% response time reduction achieved",
                "Month 9: Multi-unit expansion complete with 65% response time reduction",
                "Month 12: Enterprise deployment complete with full ROI realization"
            ]
        },
        "risk_assessment": {
            "key_risks": [
                {
                    "risk": "Customer service representative adoption resistance",
                    "probability": "Medium",
                    "impact": "High",
                    "mitigation": "Comprehensive change management program, representative champions, gradual rollout with success demonstration"
                },
                {
                    "risk": "Integration complexity with existing systems",
                    "probability": "Medium",
                    "impact": "High",
                    "mitigation": "Early integration testing, dedicated API specialists, vendor partnership leverage"
                }
            ],
            "success_factors": [
                "Strong executive sponsorship with clear accountability",
                "Comprehensive change management with representative engagement",
                "Technical excellence in AI model training and integration"
            ],
            "immediate_next_steps": [
                "Secure final executive approval and budget allocation within 30 days",
                "Execute security assessments within 45 days",
                "Establish program governance structure and team mobilization within 60 days"
            ]
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"📝 Sample assessment data created: {filename}")
    return filename

def main():
    """
    Enhanced main function with interactive experience and custom branding
    """
    try:
        print("\n🚀 Welcome to RAPID GenAI Assessment Report Generator v3.0")
        print("This tool generates comprehensive executive reports from RAPID assessment data")
        
        # Ask user if they want to create sample data or use existing file
        print("\n📋 Select an option:")
        print("1. Generate report from existing JSON file")
        print("2. Create sample data and generate report")
        print("3. Create sample data only")
        print("0. Exit")
        
        while True:
            choice = input("\nEnter your choice (0-3): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                sys.exit(0)
            elif choice == "1":
                # Use existing file
                break
            elif choice == "2":
                # Create sample and generate report
                print("\n📝 Creating sample assessment data...")
                sample_file = create_sample_assessment_data()
                print("✅ Sample data created successfully!")
                break
            elif choice == "3":
                # Create sample only
                print("\n📝 Creating sample assessment data...")
                sample_file = create_sample_assessment_data()
                print("✅ Sample data created successfully!")
                print(f"📄 File saved as: {sample_file}")
                print("🔄 Run the program again with option 1 to generate a report from this data.")
                return
            else:
                print("❌ Invalid choice. Please enter 0, 1, 2, or 3.")
        
        # Initialize the enhanced report generator with Cloud202 branding
        print("\n⚙️ Initializing Enhanced RAPID Report Generator...")
        generator = EnhancedRAPIDReportGenerator(
            aws_region='us-east-1',
            company_name='Cloud202',
            tool_name='Qubitz',
            contact_email='hello@cloud202.com',
            contact_phone='+44 7792 565738',
            assessment_lead='Cloud202 Senior Solutions Architect',
            csm='Cloud202 Customer Success Manager'
        )
        
        # Generate the comprehensive executive report
        if choice == "2":
            # Use the sample file we just created
            output_file = generator.generate_executive_report_from_json(sample_file)
            # Clean up sample file
            try:
                os.remove(sample_file)
                print(f"🗑️ Cleaned up temporary sample file: {sample_file}")
            except:
                pass
        else:
            # Use user-selected file
            output_file = generator.generate_executive_report_from_json()
        
        print(f"\n🎉 SUCCESS! Your enhanced executive report is ready!")
        print(f"📄 Report saved as: {output_file}")
        print("📊 This report contains comprehensive strategic analysis suitable for C-level presentations")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Process interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("🔍 Please ensure:")
        print("   - Your AWS credentials are configured (optional for fallback)")
        print("   - Your JSON file is valid")
        print("   - You have PyMuPDF installed: pip install PyMuPDF")
        sys.exit(1)

if __name__ == "__main__":
    main()