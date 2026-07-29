from __future__ import annotations

from .briefs_base_view import BriefSectionView


class BriefMessageView(BriefSectionView):
    section_title = "Message"
    data_method = "list_message_hierarchy"
