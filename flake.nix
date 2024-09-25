{
  description = "SDK library for building services for the IVCAP platform";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python39;

        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication;
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) defaultPoetryOverrides;

      in
      {
        packages = {
          ivcap-service-sdk-python = mkPoetryApplication {
            projectDir = ./.;
          };
          default = self.packages.${system}.ivcap-service-sdk-python;
        };

        # Shell for app dependencies.
        #
        #     nix develop
        #
        # Use this shell for developing your app.
        # and for changes to pyproject.toml and poetry.lock.
        devShells.default = pkgs.mkShell {
          packages = [ pkgs.poetry ];
          inputsFrom = [ self.packages.${system}.ivcap-service-sdk-python ];
        };

      });
}
