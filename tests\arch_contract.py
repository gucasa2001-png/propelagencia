"""
TESTE DE CONTRATO DE ARQUITETURA (Arch-Contract)
Valida fronteiras arquiteturais e integridade estrutural do Propel CRM.
"""

import os
import re
import sys

def test_arch_contract():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    crm_dir = os.path.join(base_dir, "propel_crm")
    
    violations = []

    # 1. Regra de Isolamento: Arquivos de templates não devem conter segredos ou chaves hardcoded
    templates_dir = os.path.join(crm_dir, "templates")
    if os.path.exists(templates_dir):
        for f in os.listdir(templates_dir):
            if f.endswith(".html"):
                path = os.path.join(templates_dir, f)
                with open(path, "r", encoding="utf-8") as file:
                    content = file.read()
                    if "ghp_" in content or "AIzaSy" in content:
                        violations.append(f"Segredo exposto no template: {f}")

    # 2. Regra de Contrato: Módulo de banco de dados deve expor get_db e init_db
    db_file = os.path.join(crm_dir, "database.py")
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as file:
            db_content = file.read()
            if "def get_db" not in db_content:
                violations.append("database.py deve expor a função get_db()")
            if "def init_db" not in db_content:
                violations.append("database.py deve expor a função init_db()")

    # 3. Regra de Observabilidade: app.py deve inicializar observabilidade
    app_file = os.path.join(crm_dir, "app.py")
    if os.path.exists(app_file):
        with open(app_file, "r", encoding="utf-8") as file:
            app_content = file.read()
            if "observability" not in app_content:
                violations.append("app.py deve importar e inicializar a camada de observabilidade")
            if "/api/health" not in app_content:
                violations.append("app.py deve disponibilizar o endpoint /api/health")

    if violations:
        print("[ERRO] Violações de Contrato Arquitetural detectadas:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("[SUCESSO] Contrato Arquitetural (Arch-Contract) 100% validado sem violações!")
        sys.exit(0)

if __name__ == "__main__":
    test_arch_contract()
