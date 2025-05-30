{
  description = "SDK library for building services for the IVCAP platform";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    pyproject-nix = {
      url = "github:nix-community/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, pyproject-nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Loads pyproject.toml into a high-level project representation
        project = pyproject-nix.lib.project.loadPoetryPyproject {
          projectRoot = ./.;
        };

        python = pkgs.python3;

        ivcap-service-sdk-python =
          let
            attrs = project.renderers.buildPythonPackage { inherit python; };
          in
            # Pass attributes to buildPythonPackage.
            # Here is a good spot to add on any missing or custom attributes.
            python.pkgs.buildPythonPackage (attrs // {
            });

      in
        {
          # Create a development shell containing dependencies from `pyproject.toml`
          devShells.default =
            let
              arg = project.renderers.withPackages {
                inherit python;

                # Include optional dependencies in the dev shell
                extras = [ ];
                extraPackages = ps: with ps; [ ];
              };

              # Returns a wrapped environment (virtualenv like) with all our packages
              pythonEnv = python.withPackages arg;

            in
              pkgs.mkShell {
                packages = [
                    # Our python environment, including dependencies from pyproject.yaml
                    pythonEnv

                    # Include our own package in the environment
                    ivcap-service-sdk-python

                    # Add poetry to the dev shell even though we don't use it, so we can
                    # run e.g. `poetry lock` when we update dependencies.
                    pkgs.poetry
                ];
              };

          packages.default = ivcap-service-sdk-python;
        }
    );
}
