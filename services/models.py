from sqlalchemy import Column, Integer, Float, String
from database import Base

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    # Using a name for the policy to allow for multiple policies in the future
    name = Column(String, unique=True, index=True, default="current_policy")
    lambda_val = Column(Float, nullable=False)
    d_target = Column(Float, nullable=False)