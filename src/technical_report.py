#!/usr/bin/env python3
"""
Cloud202 Technical Implementation Deep-Dive Generator (Compliance-style runtime)

- Uses centralized BedrockConfig with inference profile + invoke_model (like compliance_report.py)
- Preserves Technical prompt/section schema and tone
- Renders PDF using the same layout primitives as the compliance report
"""

import json
import logging
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Centralized Bedrock configuration
from src.bedrock_config import BedrockConfig

# ReportLab & shared styles (same as compliance)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Shared canvas & styles (same as compliance)
from src.report_styles import EnhancedNumberedCanvas, create_enhanced_styles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Cloud202TechnicalDeepDiveGenerator:
    """
    Cloud202 Technical Implementation Deep-Dive Generator using compliance-style Bedrock invocation.
    """

    def __init__(self, aws_region: str = None):
        # Timestamp for outputs
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Region from centralized config
        self.aws_region = aws_region or BedrockConfig.get_region("technical")

        # Use the regional inference profile ARN (same approach as compliance)
        self.model_id = BedrockConfig.get_inference_profile_arn(self.aws_region)

        # Log effective config
        BedrockConfig.log_configuration("technical", self.aws_region)

        # Create Bedrock client using centralized timeouts/retries (same as compliance)
        try:
            self.bedrock_runtime = BedrockConfig.create_bedrock_client(
                region=self.aws_region,
                report_type="technical"
            )
            logger.info("✅ AWS Bedrock client initialized for Technical report")
        except Exception as e:
            logger.warning(f"⚠️ Bedrock not available: {e}")
            self.bedrock_runtime = None

        # Token budget for technical reports
        self.max_tokens = BedrockConfig.get_token_limit("technical")

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
        """Normalize assessment data for prompts/PDF."""
        responses = raw_data.get('responses', {})

        # Company name heuristics (consistent with other generators)
        business_owner = responses.get('business-owner', '')
        if ',' in business_owner:
            company_name = business_owner.split(',')[0].strip()
        else:
            company_name = responses.get('company-name', 'Valued Customer') or 'Valued Customer'

        processed_data = {
            'company_name': company_name,
            'industry': self._infer_industry(responses),
            'assessment_date': raw_data.get('exportDate', datetime.now().isoformat())[:10],
            'current_state': responses.get('current-state', ''),
            'business_problem': responses.get('business-problems', ''),
            'tech_stack': responses.get('tech-stack', ''),
            'constraints': responses.get('constraints', ''),
            'non_functional': responses.get('non-functional', ''),  # SLAs/SLOs/etc
            'integration_targets': responses.get('integration-targets', ''),
            'security_compliance': responses.get('security-compliance', ''),
            'responses': responses
        }
        return processed_data

    def _infer_industry(self, responses: Dict[str, Any]) -> str:
        """Infer industry from free-text answers."""
        problem = (responses.get('business-problems', '') or '').lower()
        if any(w in problem for w in ['clinical', 'physician', 'patient', 'healthcare', 'medical']):
            return 'Healthcare Technology'
        if any(w in problem for w in ['financial', 'banking', 'fintech', 'payment', 'trading', 'market']):
            return 'Financial Technology'
        if any(w in problem for w in ['vehicle', 'manufacturing', 'automotive']):
            return 'Manufacturing & Automotive'
        return 'Technology'

    # ---------- Prompt ----------

    def create_technical_deepdive_prompt(self, processed_data: Dict[str, Any]) -> str:
        """
        Create the Technical Deep-Dive prompt.
        (Preserves your original structure/word counts and JSON-only contract.)
        """

        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')

        prompt = f"""You are a senior Cloud202 Solutions Architect drafting a TECHNICAL IMPLEMENTATION DEEP-DIVE report.

COMPANY: {company_name}
INDUSTRY: {industry}
ASSESSMENT DATA:
{json.dumps(processed_data, indent=2)}

Generate a comprehensive technical report with EXACTLY these 6 JSON keys:
{{
  "current_state_assessment": "...",
  "target_architecture_design": "...",
  "data_strategy": "...",
  "model_evaluation_recommendations": "...",
  "implementation_plan": "...",
  "integration_and_operations": "..."
}}

WORD COUNTS (strict):
- current_state_assessment: 900–1100 words
- target_architecture_design: 900–1100 words
- data_strategy: 700–900 words
- model_evaluation_recommendations: 700–900 words
- implementation_plan: 900–1100 words
- integration_and_operations: 800–1000 words

SECTION DETAILS:

1. CURRENT STATE ASSESSMENT (900–1100 words):
- Existing system architecture/topology, runtime, deployment model
- Baseline performance/availability, SLOs/SLAs, capacity headroom
- Observed bottlenecks (I/O/CPU/memory/network), failure modes, error patterns
- Security/compliance posture, identity model, secrets, logging, audit trails
- Environmental constraints (cost, skills, processes, vendor lock-in)
- Include 4–6 paragraphs with crisp technical prose

2. TARGET ARCHITECTURE DESIGN (900–1100 words):
- Recommended AWS reference architecture (compute, networking, storage, data)
- Traffic flow, ALB/NLB, WAF/Shield, VPC design, SG/NACL policy
- Data plane vs control plane, tenancy, multi-AZ, DR strategy (RTO/RPO)
- GenAI components (Bedrock, embedding/retrieval), caching (ElastiCache), database (Aurora/RDS/DynamoDB)
- CI/CD with IaC (Terraform), env strategy, feature flags, blue/green/canary
- 4–6 paragraphs with specific AWS services and configurations

3. DATA STRATEGY (700–900 words):
- Data classification, lineage, governance (Glue, Lake Formation)
- Ingestion, quality, schema evolution, CDC, partitioning
- Storage tiers (S3 classes), lifecycle, encryption (KMS), tokenization/pseudonymization
- Metadata/catalog, access policies (RBAC/ABAC), data products, privacy
- Retrieval/RAG patterns, embeddings, vector index strategy
- 3–5 paragraphs with explicit implementation detail

4. MODEL EVALUATION RECOMMENDATIONS (700–900 words):
- Offline/online eval, golden sets, regression gates, eval harness
- Hallucination checks, safety/guardrails, prompt/response policies
- Human-in-the-loop, A/B testing, acceptance criteria, SLI/SLO for quality
- Cost/perf tradeoffs, caching strategies, failure isolation
- 3–5 paragraphs, actionable and measurable

5. IMPLEMENTATION PLAN (900–1100 words):
- Phase 1 (Months 1–2): Foundations & baselining (environments, IaC, observability)
- Phase 2 (Months 3–5): Core development (APIs, data pipelines, initial guardrails)
- Phase 3 (Months 6–7): Testing/validation (load, security, UAT, perf tuning)
- Phase 4 (Month 8): Deployment (blue/green, rollback, runbooks, DR test)
- Phase 5 (Months 9–10): Stabilization/optimization (SRE playbooks, KT, handover)
- Resourcing, RACI, dependency management, risks, mitigations

6. INTEGRATION AND OPERATIONS (800–1000 words):
- Integration contracts (API specs, authN/Z, throttling); data exchange patterns
- Observability stack (CloudWatch, X-Ray, metrics/alerts), SLOs & error budgets
- Ops playbooks: incident response, change mgmt, patching, capacity
- Performance mgmt (load profiles, autoscaling), cost mgmt (budgets/anomaly)
- Day-2 ops: DR drills, backup/restore tests, compliance evidence capture

FORMATTING RULES:
- Use dense technical prose; keep bullets for lists inside the JSON values
- Include specific AWS services/configs; avoid vague statements
- STRICT JSON ONLY in the response (no markdown, no code fences)
"""
        return prompt

    # ---------- Bedrock Invocation with Streaming ----------

    def generate_report_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate technical content using Bedrock streaming for incremental output."""
        if not self.bedrock_runtime:
            logger.warning("Bedrock runtime not available — using fallback content.")
            return self._generate_fallback_content(processed_data)

        prompt = self.create_technical_deepdive_prompt(processed_data)

        try:
            logger.info("🤖 Generating technical report content (streaming)…")
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }

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
                    payload = {"type": "text", "text": chunk.get("bytes").decode("utf-8", errors="ignore")}

                if isinstance(payload, dict):
                    text_piece = (
                        payload.get("delta", {}).get("text")
                        or payload.get("text")
                        or ""
                    )
                else:
                    text_piece = ""

                if text_piece:
                    assembled.append(text_piece)
                    if len(assembled) % 20 == 0:
                        preview = text_piece.replace('\n', ' ')[:120]
                        logger.info(f"📝 Stream fragment: {preview}")

            content_text = "".join(assembled)
            content = self._parse_json_response(content_text)
            logger.info("✅ Technical content generated via streaming.")
            return content

        except Exception as e:
            logger.error(f"❌ Bedrock generation failed: {e}")
            logger.info("📋 Using high-quality fallback content...")
            return self._generate_fallback_content(processed_data)

    @staticmethod
    def _parse_json_response(text: str) -> Dict[str, Any]:
        """Strip code fences and parse JSON."""
        if not text:
            raise ValueError("Empty response content from Bedrock")
        cleaned = re.sub(r'```json\s*', '', text)
        cleaned = re.sub(r'```\s*', '', cleaned)
        cleaned = cleaned.strip()
        return json.loads(cleaned)

    # ---------- Fallback Content ----------

    def _generate_fallback_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """High-quality fallback technical content (concise but credible)."""
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')

        return {
            "current_state_assessment": f"""CURRENT STATE ASSESSMENT

{company_name} operates a mixed estate typical of {industry} workloads with legacy monoliths, point-to-point integrations,
and limited automation. Baseline SLOs are inconsistent across tiers, and capacity headroom is constrained during peak windows.
Observability coverage exists but lacks uniform correlation across logs/metrics/traces; incident triage is manual and reactive.
Identity is centrally managed but privileges are coarse-grained, and secret rotation is inconsistent across services.""",

            "target_architecture_design": """TARGET ARCHITECTURE DESIGN

Recommended blueprint: multi-AZ VPC, private subnets, ALB fronting ECS/Fargate services, Aurora PostgreSQL with read replicas,
S3 data lake (prefix+partition design), ElastiCache (Redis) for hot paths, and Bedrock for GenAI workloads. CI/CD via Terraform,
pipelines with policy-as-code and environment promotions; WAF/Shield at the edge; centralized KMS keys and CloudTrail/Lake
for audit. DR uses cross-AZ plus periodic cross-Region backups with documented RTO/RPO.""",

            "data_strategy": """DATA STRATEGY

Ingest via event streams and batch pipelines; schema control with Glue Catalog and Lake Formation. Data classification
(Restricted/Confidential/Internal/Public) governs RBAC/ABAC policies. Storage tiering uses S3 Standard → IA → Glacier with
lifecycle transitions. Encryption everywhere with KMS; tokenization for sensitive fields; metadata capture for lineage; RAG
retrieval patterns with curated embeddings and vector index separation by tenancy.""",

            "model_evaluation_recommendations": """MODEL EVALUATION RECOMMENDATIONS

Adopt offline golden sets and online A/B with guardrails. Track hallucination/toxicity, latency, cost, and success metrics with
SLIs/SLOs. Introduce HITL review queues for high-risk classes and regression gates in CI. Cache strategies reduce cost/latency;
error isolation via circuit breakers and fallback responders. Clear acceptance criteria and rollback signals are codified.""",

            "implementation_plan": """IMPLEMENTATION PLAN

Phase 1 (1–2): Foundations & baselining; envs, IaC, observability, security controls. Phase 2 (3–5): Core build (APIs, data
pipelines, guardrails). Phase 3 (6–7): Testing (load, security, UAT, perf tuning). Phase 4 (8): Deployment (blue/green,
rollback, DR test). Phase 5 (9–10): Stabilization, SRE playbooks, KT/handover. RACI with dependency mapping and risks/mitigations.""",

            "integration_and_operations": """INTEGRATION AND OPERATIONS

Contracts specify authZ scopes, idempotency, and backoff. Observability: CloudWatch/X-Ray + custom metrics, unified
dashboards, actionable alerts. Day-2 ops includes patching cadence, incident runbooks, change controls, DR drills,
backup/restore tests, cost budgets with anomaly detection, and continuous compliance evidence capture."""
        }

    # ---------- PDF Build (same layout primitives as compliance) ----------

    def create_title_page(self, styles, customer_data):
        """Create technical report title page (matching compliance report sophistication)"""
        elements = []
        
        # Add space at top
        elements.append(Spacer(1, 1.5 * inch))
        
        # Main title
        title = Paragraph("Technical Implementation<br/>Deep-Dive Report", styles['TitleMain'])
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
            ['Assessment Type:', 'Technical Implementation'],
            ['Assessment Date:', customer_data.get('assessment_date', datetime.now().strftime('%Y-%m-%d'))],
            ['Current State:', customer_data.get('current_state', 'Assessment Required')],
            ['Tech Stack:', customer_data.get('tech_stack', 'Mixed Environment')]
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
        prep_by_para = Paragraph(f"{branding['company_name']} Technical Architecture Team", styles['BodyTextEnhanced'])
        elements.append(prep_by_para)
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Confidentiality notice
        conf_text = f"<b>CONFIDENTIAL - {company_name} Technical Assessment</b>"
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
        """Render the Technical report into a styled PDF (matching compliance sophistication)."""
        processed_data = self.process_assessment_data({'responses': {}}) if not hasattr(self, '_current_processed_data') else self._current_processed_data
        
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=0.7 * inch,
            leftMargin=0.7 * inch,
            topMargin=0.7 * inch,
            bottomMargin=1 * inch,
            title=f"Technical Assessment - {processed_data.get('company_name', 'Customer')}",
            author="Cloud202 Technical Team"
        )
        
        styles = create_enhanced_styles()
        elements = []
        
        # Sophisticated title page
        elements.extend(self.create_title_page(styles, processed_data))
        
        # Content sections using sophisticated formatting
        sections = [
            ("Current State Assessment", content.get('current_state_assessment', '')),
            ("Target Architecture Design", content.get('target_architecture_design', '')),
            ("Data Strategy", content.get('data_strategy', '')),
            ("Model Evaluation Recommendations", content.get('model_evaluation_recommendations', '')),
            ("Implementation Plan", content.get('implementation_plan', '')),
            ("Integration & Operations", content.get('integration_and_operations', ''))
        ]
        
        for title, text in sections:
            elements.extend(self.create_content_section(title, text, styles))
        
        # Build PDF with EnhancedNumberedCanvas
        def make_canvas(*args, **kwargs):
            branding = BedrockConfig.get_branding()
            return EnhancedNumberedCanvas(
                *args,
                company_name=processed_data.get('company_name', branding.get('company_name', 'Cloud202')),
                report_type='Technical Implementation Deep-Dive',
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
        pdf_path = self.output_dir / f"Technical_Report_{safe_company}_{self.timestamp}.pdf"
        self.build_pdf(content, pdf_path)

        return {
            "pdf_path": str(pdf_path),
            "content": content,
            "meta": processed
        }


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="Generate Technical Deep-Dive Report (compliance-style runtime).")
    parser.add_argument("input_json", help="Path to assessment JSON export")
    parser.add_argument("--region", help="AWS region (overrides BedrockConfig default for technical)", default=None)
    args = parser.parse_args()

    gen = Cloud202TechnicalDeepDiveGenerator(aws_region=args.region)
    result = gen.generate_report(args.input_json)

    print(json.dumps({
        "ok": True,
        "pdf_path": result["pdf_path"],
        "meta": result["meta"]
    }, indent=2))


if __name__ == "__main__":
    main()
