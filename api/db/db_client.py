from api.db.agent_trigger_client import AgentTriggerClient
from api.db.api_key_client import APIKeyClient
from api.db.campaign_client import CampaignClient
from api.db.campaign_ops_client import CampaignOpsClient
from api.db.cost_attribution_client import CostAttributionClient
from api.db.disposition_client import DispositionClient
from api.db.embed_token_client import EmbedTokenClient
from api.db.folder_client import FolderClient
from api.db.integration_client import IntegrationClient
from api.db.knowledge_base_client import KnowledgeBaseClient
from api.db.organization_client import OrganizationClient
from api.db.organization_configuration_client import OrganizationConfigurationClient
from api.db.organization_usage_client import OrganizationUsageClient
from api.db.outcomes_client import OutcomesClient
from api.db.reports_client import ReportsClient
from api.db.script_library_client import ScriptLibraryClient
from api.db.stepsales_client import StepsalesClient
from api.db.telephony_configuration_client import TelephonyConfigurationClient
from api.db.telephony_phone_number_client import TelephonyPhoneNumberClient
from api.db.tool_client import ToolClient
from api.db.training_client import TrainingClient
from api.db.user_client import UserClient
from api.db.webhook_credential_client import WebhookCredentialClient
from api.db.webhook_delivery_client import WebhookDeliveryClient
from api.db.workflow_client import WorkflowClient
from api.db.workflow_recording_client import WorkflowRecordingClient
from api.db.workflow_run_client import WorkflowRunClient
from api.db.workflow_run_text_session_client import WorkflowRunTextSessionClient
from api.db.workflow_template_client import WorkflowTemplateClient


class DBClient(
    WorkflowClient,
    WorkflowRunClient,
    WorkflowRunTextSessionClient,
    UserClient,
    OrganizationClient,
    OrganizationConfigurationClient,
    OrganizationUsageClient,
    IntegrationClient,
    WorkflowTemplateClient,
    CampaignClient,
    ReportsClient,
    APIKeyClient,
    EmbedTokenClient,
    AgentTriggerClient,
    WebhookCredentialClient,
    WebhookDeliveryClient,
    ToolClient,
    KnowledgeBaseClient,
    WorkflowRecordingClient,
    TelephonyConfigurationClient,
    TelephonyPhoneNumberClient,
    FolderClient,
    StepsalesClient,
    OutcomesClient,
    DispositionClient,
    ScriptLibraryClient,
    CampaignOpsClient,
    CostAttributionClient,
    TrainingClient,
):
    """
    Unified database client that combines all specialized database operations.
    """

    pass
