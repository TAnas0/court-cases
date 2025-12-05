from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Participant(Base):
    __tablename__ = 'participants'

    id = Column(Integer, primary_key=True)
    participant_code = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    case_id = Column(Integer, ForeignKey('cases.id')) # TODO Many-to-many relationship as a particpant can be defendant in a case, and complainant in another

    # TODO address

    # Relationships
    # case = relationship("Case", back_populates="participants")

    def __repr__(self):
        return f"<Participant(full_name='{self.full_name}', participant_code='{self.participant_code}')>"
