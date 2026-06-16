from app.features.translation.requests import TranslateRequest
from app.ports import SupabasePortDep


class TranslateService:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, request: TranslateRequest) -> None:
        pass
