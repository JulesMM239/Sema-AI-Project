from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
import argon2
from app.core.settings import settings

pwd_context = CryptContext(
    schemes=["argon2"], 
    deprecated="auto",
    # Paramètres optimisés pour Argon2
    argon2__memory_cost=65536,      # 64 Mo - adapté à la mémoire disponible
    argon2__time_cost=3,           # 3 itérations - bon équilibre sécurité/performance
    argon2__parallelism=4,         # 4 threads/processus parallèles
    argon2__hash_len=32,           # Longueur du hash: 32 octets (256 bits)
    argon2__salt_len=16,           # Longueur du sel: 16 octets
    argon2__type="ID"              # Type ID pour Argon2id (recommandé)
)

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int = 60 * 24 * 7, extra: Optional[dict] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": subject, "exp": expire}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


# Fonction optionnelle pour la migration depuis bcrypt (si vous avez des utilisateurs existants)
def verify_password_with_migration(
    plain_password: str, 
    hashed_password: str, 
    on_migration_callback=None
) -> bool:
    """
    Vérifie le mot de passe avec support de migration depuis bcrypt.
    
    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash stocké
        on_migration_callback: Callback appelé si migration nécessaire
    
    Returns:
        True si le mot de passe est valide
    """
    # Créer un contexte bcrypt pour la migration
    bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # D'abord essayer avec Argon2
    if pwd_context.verify(plain_password, hashed_password):
        return True
    
    # Si échec, essayer avec bcrypt (pour la migration)
    if bcrypt_context.verify(plain_password, hashed_password):
        # Migration vers Argon2
        new_hash = hash_password(plain_password)
        if on_migration_callback:
            on_migration_callback(new_hash)
        return True
    
    return False