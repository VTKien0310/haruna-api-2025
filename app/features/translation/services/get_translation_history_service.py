from app.ports.supabase import SupabasePortDep


class GetTranslationHistoryService:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, user_id: str) -> None:
        pass
