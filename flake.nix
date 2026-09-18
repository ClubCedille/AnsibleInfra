{
  description = "Environnement de dev pour AnsibleInfra (venv Python + Ansible)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python3
            git
            gnumake
            openssh
            sshpass
          ];

          shellHook = ''
            # Crée/rafraîchit le venv comme `make venv`, pour que les
            # commandes ansible-playbook / ansible-lint fonctionnent aussi
            # en dehors de make (édition, debug interactif).
            if [ ! -d .venv ] || [ requirements.txt -nt .venv/.deps-installed ]; then
              echo "[flake] (ré)installation du venv depuis requirements.txt..."
              python3 -m venv .venv
              .venv/bin/pip install --upgrade pip >/dev/null
              .venv/bin/pip install -r requirements.txt
              touch .venv/.deps-installed
            fi
            source .venv/bin/activate
          '';
        };
      });
}
