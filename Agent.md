# Inventory Management — yêu cầu và tiến độ

Nguồn yêu cầu: `Requirement.xlsx` (`Sheet1`). Cập nhật tiến độ: 07/11/2026 (Asia/Bangkok). Tài liệu này tóm tắt yêu cầu của project Inventory Management; các file WS8/WS10 trong workspace là bài tập tham khảo, không phải nguồn yêu cầu của project này.

## 1. Mục tiêu và phạm vi

Xây dựng ứng dụng web quản lý tồn kho bằng **Nexacro** cho frontend và **xapi** (Spring Boot, Nexacro Java XAPI) cho backend. Người dùng có thể đăng nhập/đăng ký, xem và thêm sản phẩm, theo dõi chi tiết sản phẩm và quản lý nhà cung cấp.

Yêu cầu đào tạo đi kèm: sử dụng Dataset, Grid, transaction, popup, validation, common framework; tổ chức màn hình hợp lý; tối ưu hiệu năng, cache và xử lý Grid; triển khai ứng dụng và kiểm thử đơn vị.

Thiết kế tham chiếu: [Inventory Management Dashboard trên Figma](https://www.figma.com/design/kWRQSa8gOqUFSlE446fnYz/Inventory-Management-Dashboard--Community-?node-id=477-882).

## 2. Yêu cầu từng màn hình

| Màn hình | Thành phần và chức năng theo `Requirement.xlsx` | Tiến độ FE |
| --- | --- | --- |
| Login | Email, mật khẩu, Remember me, Forgot password, nút Login và điều hướng Sign up; kiểm tra định dạng email/mật khẩu bắt buộc, báo lỗi chung, gửi transaction đăng nhập, lưu session token. | Đã tạo form và validation; đăng nhập hiện chỉ là chế độ xem trước. Remember me/Forgot password chưa nối chức năng thực. Chưa có API và token. |
| Sign Up | Tên, email, mật khẩu, xác nhận mật khẩu; kiểm tra trường bắt buộc, mật khẩu tối thiểu 8 ký tự, email duy nhất, thông báo lỗi. | Đã tạo form và validation cục bộ; chưa kiểm tra email duy nhất hoặc tạo tài khoản qua API. |
| Inventory List | Chỉ số dashboard; Grid gồm tên sản phẩm, giá mua, số lượng, ngưỡng tồn, hạn sử dụng, trạng thái; tìm kiếm, lọc, phân trang, tải xuống, mở popup thêm sản phẩm và mở chi tiết khi chọn dòng; tô màu In stock/Low stock/Out of stock. | Đã tạo giao diện, dữ liệu mẫu trong bộ nhớ, tìm kiếm, lọc, phân trang, trạng thái và điều hướng chi tiết. Download và tải dữ liệu qua transaction chưa hoàn thành. |
| Add New Product | Popup với ảnh, tên, ID, danh mục, giá mua, số lượng, đơn vị, hạn sử dụng, ngưỡng tồn; kiểm tra dữ liệu, lưu qua transaction và làm mới danh sách. | Đã tạo popup, dropdown, chọn tệp ảnh và validation; thêm vào dữ liệu bộ nhớ và làm mới danh sách. Chưa upload/lưu qua API. |
| Product Detail | Ảnh, thông tin sản phẩm, nhà cung cấp, vị trí tồn kho; tab Overview, Purchases, Adjustments, History; tải theo ID và hiển thị thông tin liên quan. | Đã tạo form, tải sản phẩm đang chọn từ dữ liệu mẫu và hiển thị thông tin cơ bản. Ảnh, vị trí tồn và dữ liệu các tab cần API. |
| Suppliers List | Grid gồm tên nhà cung cấp, sản phẩm, liên hệ, email, loại nhận trả hàng và hàng đang về; nút thêm, lọc, sắp xếp và tải dữ liệu. | Đã tạo Grid, tìm kiếm, lọc, sắp xếp, popup thêm và dữ liệu mẫu. Chưa tải qua API. |
| Add New Supplier | Popup với ảnh, tên, sản phẩm, danh mục, giá mua, số liên hệ, loại nhận trả hàng; kiểm tra dữ liệu và lưu qua transaction. | Đã tạo popup, chọn tệp ảnh, dropdown loại và validation; thêm vào bộ nhớ. Chưa upload/lưu qua API. |

## 3. Yêu cầu dùng chung và backend

- **Common code:** tối thiểu 5 service/hàm tái sử dụng, gồm transaction, lấy mã/dữ liệu chung, validation, binding và thông báo. FE hiện có `gfnEmpty`, `gfnEmail`, `gfnNumber`, `gfnMessage`, `gfnNavigate`, `gfnPopup`, `gfnTransaction`, `gfnSeed` trong `Inventory_FE/lib/InventoryCommon.xjs`. Các hàm lấy mã và binding dùng chung vẫn cần bổ sung khi tích hợp API.
- **Database:** thiết kế schema theo nghiệp vụ sản phẩm, nhà cung cấp và tài khoản; trainer sẽ review.
- **API:** tạo endpoint cho các chức năng trong bảng trên, dùng common transaction module phía Nexacro; có validation và truy xuất dữ liệu dùng chung.
- **Tham khảo BE:** `xapi/xapi` hiện là project mẫu với API Employee, chưa có endpoint authentication, product hoặc supplier.
- **Vận hành:** bổ sung cache level phù hợp, kiểm thử đơn vị, kiểm thử giao diện/transaction, tối ưu hiệu năng và triển khai.

## 4. Tiến độ thực tế

| Hạng mục | Trạng thái | Bằng chứng / ghi chú |
| --- | --- | --- |
| Đọc `Requirement.xlsx` | Hoàn thành | Đã tổng hợp 7 màn hình, common code và yêu cầu BE trong tài liệu này. |
| Tạo project FE độc lập | Hoàn thành phần khung | `Inventory_FE/Inventory_FE.xprj`, 7 form trong `Inventory_FE/forms/`, CSS và common library. Project Nexacro WS8/WS10 cũ được giữ riêng. |
| Luồng FE với dữ liệu mẫu | Hoàn thành bản xem trước | Điều hướng, popup, validation, tìm kiếm/lọc, phân trang và sắp xếp hoạt động trên dữ liệu trong bộ nhớ; dữ liệu thêm mới mất khi đóng ứng dụng. |
| Cập nhật giao diện theo Figma | Đang thực hiện | Đã chỉnh source của 7 form sang khung 1440 × 960, nền sáng, màu xanh dương, sidebar/top bar và bố cục card/modal theo mẫu. Đây là bản triển khai theo quan sát bằng quyền Viewer; chưa xác nhận độ khớp khi chạy Nexacro. Chi tiết ở mục 6. |
| Tích hợp xapi | Chưa bắt đầu | BE mẫu chỉ có Employee. Chưa có contract/API cho 7 màn hình. |
| Kiểm thử FE | Một phần | `python Inventory_FE/validate_frontend.py` đã qua kiểm tra XML, cú pháp JavaScript và event handler. Chưa chạy thử trực quan trong Nexacro Studio/NRE. |
| Unit test, hiệu năng, triển khai | Chưa bắt đầu | Chờ API và luồng nghiệp vụ hoàn chỉnh. |

## 5. Kết quả đối chiếu trước khi chỉnh (07/11/2026)

**Đây là ghi nhận của bản FE ban đầu, trước lần chỉnh giao diện ở mục 6.** Lúc đó form FE cao 800 px, dùng sidebar xanh đậm và tông xanh lá; frame Figma cao 960 px, dùng nền sáng, sidebar trắng và nhận diện KANBAN xanh dương.

| Form FE | Sai khác chính với Figma |
| --- | --- |
| Login | Figma có nền trắng và logo KANBAN lớn bên trái; FE có panel xanh đậm, chữ giới thiệu và logo Invento. |
| SignUp | Cùng sai khác nhận diện/bố cục Login. Figma chỉ thể hiện Name, Email, Password; requirement yêu cầu thêm Confirm password nên FE có trường này. |
| InventoryList | Figma có top bar, thẻ Overall Inventory chia 4 nhóm và Grid sản phẩm trong card; FE không có top bar, dùng 3 thẻ chỉ số riêng, khoảng cách và vị trí khác. |
| ProductForm | Figma là modal hẹp một cột nằm trên Inventory với nền mờ; FE là popup hai cột, thêm trường Supplier và bố trí chọn ảnh ở cuối. |
| ProductDetail | Figma có tab ở đầu card, nút Edit/Download, ảnh bên phải, bảng Stock Locations; FE đặt tab cuối màn, ảnh placeholder bên trái và chưa có bảng vị trí tồn. |
| SupplierList | Cột Grid tương đối phù hợp, nhưng FE thiếu top bar, sidebar/bố cục/card và phân trang theo mẫu. Figma ghi nút “Add Product” trên màn Suppliers, trong khi requirement yêu cầu Add Supplier và FE dùng Add supplier. |
| SupplierForm | Figma là modal một cột trên Suppliers với ảnh ở đầu và nút chọn loại dạng hai lựa chọn; FE là popup hai cột, ảnh ở cuối và Combo cho loại. |

## 6. Thay đổi FE đang thực hiện theo Figma (07/11/2026)

- Thêm `Inventory_FE/figma_layout.py`; `build_frontend.py` hiện tự áp dụng bước chuyển bố cục này sau khi tạo 7 form. File `Application.xadl` và 5 form chính đã chuyển sang **1440 × 960**; `ProductForm` là **500 × 800**, `SupplierForm` là **500 × 730**.
- Chuyển CSS từ xanh lá/sidebar tối sang nền sáng, sidebar trắng và nút xanh dương. Thêm thanh trên cùng với ô tìm kiếm, khu vực thông báo/avatar dạng giao diện.
- Login/SignUp chuyển sang nền trắng, khối nhận diện KANBAN bên trái và form bên phải. Giữ `Confirm password` theo `Requirement.xlsx` dù Figma không thể hiện trường này.
- InventoryList chuyển sang card **Overall Inventory** 4 nhóm và card Products, bố trí lại nút thêm/lọc/download, Grid và phân trang.
- SupplierList chuyển sang card, Grid và phân trang theo khung Figma; giữ nhãn **Add Supplier** theo nghiệp vụ trong workbook (mẫu Figma ghi “Add Product” ở màn Suppliers).
- ProductForm/SupplierForm chuyển từ bố cục hai cột sang modal một cột, khu vực chọn ảnh ở đầu. ProductForm bỏ trường Supplier không có trong yêu cầu thêm sản phẩm; SupplierForm hiển thị 6 trường như mẫu. Email/OnTheWay chưa có ô nhập trong modal và hiện nhận giá trị mặc định khi thêm dữ liệu mẫu.
- ProductDetail chuyển tab lên đầu card, thêm nút Edit/Download, chuyển ảnh sang phải và bố trí lại các mục chi tiết, nhà cung cấp, vị trí tồn kho. Ảnh sản phẩm và dữ liệu stock location vẫn là placeholder.
- Đã chạy `python Inventory_FE/build_frontend.py` và `python Inventory_FE/validate_frontend.py`: **7 form, 14 file XML/source hợp lệ; cú pháp JavaScript và event handler đạt kiểm tra tĩnh**.

**Chưa hoàn tất:** Logo KANBAN đang là ký hiệu/chữ thay thế; chưa lấy được file logo gốc qua quyền Viewer/Figma MCP. Chưa có ảnh/biểu tượng gốc khác từ thiết kế. Đã mở Nexacro Studio nhưng công cụ điều khiển chưa đọc được cửa sổ làm việc, vì vậy chưa chạy/so sánh ảnh giao diện thực tế. Các nút Edit/Download và dữ liệu chi tiết còn chờ API. Không đánh dấu bản FE là khớp Figma trước khi kiểm tra runtime.

## 7. Công việc tiếp theo

1. Mở `Inventory_FE/Inventory_FE.xprj` trong Nexacro Studio, chạy/QuickView cả 7 form và chụp ảnh đối chiếu với Figma; sửa lỗi runtime, control, khoảng cách và trạng thái tương tác nếu có.
2. Lấy logo/asset gốc từ Figma bằng cách xuất file hợp lệ hoặc dùng bản sao có quyền editor cho tài khoản Figma MCP; thay các ký hiệu/placeholder hiện tại. Kiểm tra kích thước và vị trí asset trên từng màn.
3. Rà lại modal trên lớp nền mờ và luồng chọn ảnh trong Nexacro runtime; xác nhận các trường chênh giữa Figma và `Requirement.xlsx` mà vẫn giữ đủ nghiệp vụ.
4. Chốt schema và contract Dataset/transaction cho authentication, product, supplier, product detail, stock location và upload ảnh; triển khai endpoint trong `xapi/xapi`.
5. Nối FE với API qua `gfnTransaction`, xử lý callback/lỗi, token phiên, làm mới Dataset và chức năng download.
6. Hoàn thiện các tab chi tiết, cache, unit test, kiểm thử tích hợp và triển khai.

## 8. Quy tắc cập nhật tiến độ

Sau mỗi phần việc, cập nhật trạng thái trong bảng trên và ghi rõ bằng chứng kiểm tra. Chỉ đánh dấu **Hoàn thành** khi chức năng đã chạy với API thực và được kiểm thử; trạng thái giao diện/dữ liệu mẫu phải ghi là **bản xem trước**.
