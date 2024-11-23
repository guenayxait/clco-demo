import pulumi
from pulumi_azure_native import resources, storage, web
import os
import zipfile
import pulumi.asset as assets

# 1. Create an Azure Resource Group
resource_group = resources.ResourceGroup("resource_group", location="westus")

# 2. Create an Azure Storage Account
account = storage.StorageAccount(
    "storageaccount",
    resource_group_name=resource_group.name,
    sku={
        "name": storage.SkuName.STANDARD_LRS,
    },
    kind=storage.Kind.STORAGE_V2,
)

# 3. Create a Blob Container for deployment files
blob_container = storage.BlobContainer(
    "appcontainer",
    resource_group_name=resource_group.name,
    account_name=account.name,
    public_access=storage.PublicAccess.NONE,
)

# 4. Define paths
app_directory_path = os.path.abspath(os.path.join(os.getcwd(), "..", "app"))  # Verzeichnis: clco-demo/app
zip_file_path = os.path.join(os.getcwd(), "app.zip")  # Ziel: app.zip

# Debugging: Prüfen, ob das Verzeichnis gefunden wird
print(f"Current working directory: {os.getcwd()}")
print(f"Looking for app directory at: {app_directory_path}")

# 5. Prüfen, ob das Verzeichnis existiert und ZIP erstellen
if not os.path.exists(app_directory_path) or not os.path.isdir(app_directory_path):
    raise FileNotFoundError(f"Directory {app_directory_path} not found or is not a directory.")

with zipfile.ZipFile(zip_file_path, "w") as zf:
    for root, _, files in os.walk(app_directory_path):
        for file in files:
            file_path = os.path.join(root, file)
            zf.write(file_path, arcname=os.path.relpath(file_path, app_directory_path))

# 6. Upload the ZIP file to the Blob Container
app_blob = storage.Blob(
    "appzipblob",
    resource_group_name=resource_group.name,
    account_name=account.name,
    container_name=blob_container.name,
    source=assets.FileAsset(zip_file_path),  # ZIP-Datei hochladen
)

# 7. Create an App Service Plan
app_service_plan = web.AppServicePlan(
    "appserviceplan",
    resource_group_name=resource_group.name,
    sku=web.SkuDescriptionArgs(
        name="F1",        # Kostenloser Plan (F1)
        tier="Free",      # Kostenlose Tier
        size="F1",
    ),
)

# 8. Create a Web App referencing the Blob URL in SiteConfigArgs
web_app = web.WebApp(
    "webapp",
    resource_group_name=resource_group.name,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
        app_settings=[
            web.NameValuePairArgs(
                name="WEBSITE_RUN_FROM_PACKAGE",
                value=app_blob.url,  # URL zur hochgeladenen ZIP-Datei
            ),
            web.NameValuePairArgs(
                name="PORT",
                value="8000",  # Setze den Port auf 8000
            ),
        ],
        app_command_line="python -m flask run --host=0.0.0.0 --port=8000",  # Startbefehl für Flask
    ),
)

# 9. Exportiere die Web App URL
pulumi.export("web_app_url", web_app.default_host_name)

# 10. Optional: Exportiere die URL der hochgeladenen ZIP-Datei
pulumi.export("app_blob_url", app_blob.url)
