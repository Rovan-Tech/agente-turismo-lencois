import enum

from sqlalchemy import Boolean, Float, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DifficultyLevel(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class Tour(Base):
    __tablename__ = "tours"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str] = mapped_column(String(1000))
    dificuldade_fisica: Mapped[DifficultyLevel] = mapped_column(
        String(10), default=DifficultyLevel.MEDIA
    )
    caminhada_areia_minutos: Mapped[int] = mapped_column(default=0)
    acessivel_idosos: Mapped[bool] = mapped_column(Boolean, default=False)
    acessivel_cadeirantes: Mapped[bool] = mapped_column(Boolean, default=False)
    acessivel_criancas_pequenas: Mapped[bool] = mapped_column(Boolean, default=False)
    duracao_horas: Mapped[float] = mapped_column(Float, default=0.0)
    faixa_etaria_recomendada: Mapped[str] = mapped_column(String(200), default="")
    preco_reais: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    def to_catalog_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "descricao": self.descricao,
            "dificuldade_fisica": self.dificuldade_fisica,
            "caminhada_areia_minutos": self.caminhada_areia_minutos,
            "acessivel_idosos": self.acessivel_idosos,
            "acessivel_cadeirantes": self.acessivel_cadeirantes,
            "acessivel_criancas_pequenas": self.acessivel_criancas_pequenas,
            "duracao_horas": self.duracao_horas,
            "faixa_etaria_recomendada": self.faixa_etaria_recomendada,
            "preco_reais": float(self.preco_reais),
        }
