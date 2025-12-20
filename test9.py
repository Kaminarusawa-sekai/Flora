

from interaction.interaction_handler import InteractionHandler
from interaction.common import UserInputDTO, SystemResponseDTO

from interaction.capabilities import get_capability_manager,init_capabilities


init_capabilities()



interaction_handler = InteractionHandler()
response = interaction_handler.handle_user_input(UserInputDTO(
    session_id="123",
    user_id="456",
    utterance="继续刚才的任务"))
print(response.response_text)